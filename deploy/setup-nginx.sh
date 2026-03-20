#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Setup script for api.fundowallet.com reverse proxy
# Run on the Vultr host as root:  bash deploy/setup-nginx.sh
# ──────────────────────────────────────────────────────────────
set -euo pipefail

DOMAIN="api.fundowallet.com"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Nginx and Certbot..."
apt-get update -qq
apt-get install -y -qq nginx certbot python3-certbot-nginx

echo "==> Copying rate-limit config..."
cp "$SCRIPT_DIR/nginx/rate-limit.conf" /etc/nginx/conf.d/rate-limit.conf

echo "==> Copying proxy_params..."
cp "$SCRIPT_DIR/nginx/proxy_params" /etc/nginx/proxy_params

echo "==> Copying site config..."
cp "$SCRIPT_DIR/nginx/api.fundowallet.com" /etc/nginx/sites-available/api.fundowallet.com
ln -sf /etc/nginx/sites-available/api.fundowallet.com /etc/nginx/sites-enabled/api.fundowallet.com

# Remove default site if it exists
rm -f /etc/nginx/sites-enabled/default

echo "==> Obtaining SSL certificate..."
# Temporarily use HTTP-only config for certbot
cat > /tmp/nginx-certbot-temp.conf << 'TMPEOF'
server {
    listen 80;
    server_name api.fundowallet.com;
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    location / {
        return 444;
    }
}
TMPEOF
cp /tmp/nginx-certbot-temp.conf /etc/nginx/sites-available/api.fundowallet.com
nginx -t && systemctl reload nginx

certbot certonly --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@fundowallet.com

echo "==> Restoring full site config..."
cp "$SCRIPT_DIR/nginx/api.fundowallet.com" /etc/nginx/sites-available/api.fundowallet.com

echo "==> Testing Nginx config..."
nginx -t

echo "==> Reloading Nginx..."
systemctl reload nginx
systemctl enable nginx

echo "==> Setting up auto-renewal..."
systemctl enable certbot.timer
systemctl start certbot.timer

echo ""
echo "============================================"
echo "  DONE! api.fundowallet.com is live"
echo "============================================"
echo ""
echo "  HTTPS:  https://api.fundowallet.com/health"
echo "  Docs:   https://api.fundowallet.com/docs"
echo ""
echo "  Rate limits:"
echo "    General API:  30 req/s per IP"
echo "    Auth:          5 req/s per IP"
echo ""
echo "  Logs:"
echo "    Access: /var/log/nginx/api.fundowallet.com.access.log"
echo "    Error:  /var/log/nginx/api.fundowallet.com.error.log"
echo ""
echo "  IMPORTANT: Make sure your DNS A record for"
echo "  $DOMAIN points to this server's IP."
echo "============================================"
