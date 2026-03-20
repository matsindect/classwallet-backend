#!/usr/bin/env bash
# ------------------------------------------------------------------
# Class Wallet — Remote Deployment Script
# Called by the GitHub Actions pipeline over SSH.
# Files are synced via rsync before this script runs.
# ------------------------------------------------------------------
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/dev/class-wallet-backend}"
COMPOSE_FILE="docker-compose.prod.yml"

echo "==> Deploying Class Wallet Backend"
echo "    Directory: ${APP_DIR}"
echo "    Compose:   ${COMPOSE_FILE}"
echo "    Time:      $(date -u +%Y-%m-%dT%H:%M:%SZ)"

cd "${APP_DIR}"

# --- Validate .env exists and contains required variables ---
echo "==> Validating environment file..."
if [ ! -f .env ]; then
    echo "==> ERROR: .env file not found at ${APP_DIR}/.env"
    echo "    The pipeline should have written this file before running deploy.sh"
    exit 1
fi

REQUIRED_VARS=(
    "DATABASE_URL"
    "JWT_SECRET_KEY"
    "POSTGRES_DB"
    "POSTGRES_USER"
    "POSTGRES_PASSWORD"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" .env; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "==> ERROR: .env is missing required variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "    - ${var}"
    done
    echo ""
    echo "    Update the ENV_FILE_CONTENT secret in GitHub and re-run the pipeline."
    exit 1
fi

echo "    All required variables present."

# --- Check for new variables in .env.example not in .env ---
if [ -f .env.example ]; then
    echo "==> Checking for new variables in .env.example..."
    WARN_VARS=()
    while IFS= read -r line; do
        # Skip comments and blank lines
        [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
        VAR_NAME=$(echo "$line" | cut -d '=' -f1)
        if ! grep -q "^${VAR_NAME}=" .env; then
            WARN_VARS+=("$VAR_NAME")
        fi
    done < .env.example

    if [ ${#WARN_VARS[@]} -gt 0 ]; then
        echo "    WARNING: .env.example has variables not in .env:"
        for var in "${WARN_VARS[@]}"; do
            echo "      - ${var}"
        done
        echo "    These may be new config options. Update ENV_FILE_CONTENT if needed."
    else
        echo "    .env is in sync with .env.example."
    fi
fi

# --- Build images ---
echo "==> Building Docker images..."
docker compose -f "${COMPOSE_FILE}" build --no-cache

# --- Run database migrations before swapping containers ---
echo "==> Running database migrations..."
docker compose -f "${COMPOSE_FILE}" run --rm \
    app alembic upgrade head

# --- Bring up services ---
echo "==> Starting services..."
docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans

# --- Wait for health check ---
echo "==> Waiting for health check..."
MAX_RETRIES=15
RETRY_INTERVAL=4
for i in $(seq 1 $MAX_RETRIES); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "==> Health check passed on attempt ${i}"
        break
    fi
    if [ "$i" -eq "$MAX_RETRIES" ]; then
        echo "==> ERROR: Health check failed after ${MAX_RETRIES} attempts"
        echo "==> Container logs:"
        docker compose -f "${COMPOSE_FILE}" logs --tail=50 app
        exit 1
    fi
    echo "    Attempt ${i}/${MAX_RETRIES} — waiting ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

# --- Sync Nginx config if changed ---
echo "==> Syncing Nginx config..."
NGINX_CHANGED=false

if [ -f deploy/nginx/rate-limit.conf ]; then
    if ! diff -q deploy/nginx/rate-limit.conf /etc/nginx/conf.d/rate-limit.conf > /dev/null 2>&1; then
        sudo /bin/cp deploy/nginx/rate-limit.conf /etc/nginx/conf.d/rate-limit.conf
        NGINX_CHANGED=true
        echo "    Updated rate-limit.conf"
    fi
fi

if [ -f deploy/nginx/proxy_params ]; then
    if ! diff -q deploy/nginx/proxy_params /etc/nginx/proxy_params > /dev/null 2>&1; then
        sudo /bin/cp deploy/nginx/proxy_params /etc/nginx/proxy_params
        NGINX_CHANGED=true
        echo "    Updated proxy_params"
    fi
fi

if [ -f deploy/nginx/api.fundowallet.com ]; then
    if ! diff -q deploy/nginx/api.fundowallet.com /etc/nginx/sites-available/api.fundowallet.com > /dev/null 2>&1; then
        sudo /bin/cp deploy/nginx/api.fundowallet.com /etc/nginx/sites-available/api.fundowallet.com
        NGINX_CHANGED=true
        echo "    Updated api.fundowallet.com site config"
    fi
fi

if [ "$NGINX_CHANGED" = true ]; then
    echo "==> Validating Nginx config..."
    if sudo /usr/sbin/nginx -t 2>&1; then
        echo "==> Reloading Nginx..."
        sudo /usr/bin/systemctl reload nginx
        echo "    Nginx reloaded with updated config."
    else
        echo "==> ERROR: Nginx config test failed! Keeping previous config."
        exit 1
    fi
else
    echo "    No Nginx config changes detected."
fi

# --- Cleanup old images ---
echo "==> Pruning dangling images..."
docker image prune -f

echo "==> Deployment complete!"
