# ──────────────────────────────────────────────────────────────
# Rate limiting zones (placed in http context via /etc/nginx/conf.d/)
# ──────────────────────────────────────────────────────────────
# If using this file directly in sites-available, add the limit_req_zone
# directives to /etc/nginx/conf.d/rate-limit.conf instead (see setup script).

# Bot filtering — must be in http context, so placed in a separate conf file.
# See deploy/nginx/bot-filter.conf

server {
    listen 80;
    server_name api.fundowallet.com;

    # Redirect all HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.fundowallet.com;

    # ── SSL (managed by certbot) ──────────────────────────────
    ssl_certificate     /etc/letsencrypt/live/api.fundowallet.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.fundowallet.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;

    # ── Security headers ──────────────────────────────────────
    add_header X-Content-Type-Options    "nosniff" always;
    add_header X-Frame-Options           "DENY" always;
    add_header X-XSS-Protection          "1; mode=block" always;
    add_header Referrer-Policy           "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # ── Bot & scanner filtering (via map in bot-filter.conf) ──
    if ($bad_bot) {
        return 403;
    }

    # Block empty or missing Host header
    if ($host !~* ^api\.fundowallet\.com$) {
        return 444;
    }

    # ── Block exploit paths ───────────────────────────────────
    location ~* ^/(wp-admin|wp-login|wp-content|wp-includes|wordpress) {
        return 404;
    }
    location ~* ^/(admin|phpmyadmin|pma|myadmin|mysql|phpinfo) {
        return 404;
    }
    location ~* \.(php|asp|aspx|jsp|cgi)$ {
        return 404;
    }
    location ~* ^/(\.env|\.git|\.htaccess|\.htpasswd) {
        return 404;
    }
    location ~* ^/(shell|eval-stdin|cgi-bin) {
        return 404;
    }

    # ── Rate limiting ─────────────────────────────────────────
    # Auth endpoints: 5 requests/second per IP (brute-force protection)
    location /auth/login {
        limit_req zone=auth_strict burst=3 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/proxy_params;
    }

    location /auth/ {
        limit_req zone=auth_strict burst=5 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/proxy_params;
    }

    # ── Main proxy: 30 requests/second per IP ─────────────────
    location / {
        limit_req zone=api_general burst=20 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:8000;
        include /etc/nginx/proxy_params;
    }

    # ── Logging ───────────────────────────────────────────────
    access_log /var/log/nginx/api.fundowallet.com.access.log;
    error_log  /var/log/nginx/api.fundowallet.com.error.log;

    # ── Limits ────────────────────────────────────────────────
    client_max_body_size 10M;
    proxy_read_timeout   30s;
    proxy_connect_timeout 10s;
}
