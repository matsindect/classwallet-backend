# Class Wallet Backend — CI/CD Pipeline & Infrastructure Guide

---

## 1. Executive Summary

| Aspect | Finding |
|---|---|
| **Architecture** | Modular monolith — FastAPI REST API with 8 domain modules |
| **Deployment model** | Docker Compose on a single server via SSH |
| **Database** | PostgreSQL 16 (Docker container with persistent volume) |
| **Background work** | In-process asyncio poller (ZB Bank integration) — no separate worker |
| **Infrastructure needed** | 1 Linux server, Docker, Compose, reverse proxy, PostgreSQL |
| **CI/CD strategy** | GitHub Actions → lint/test/scan/build → SSH deploy to dev server |

The pipeline triggers **only** when a pull request is merged into the `dev` branch and **only** when application or infrastructure files have changed.

---

## 2. Codebase Architecture Findings

### Application Structure

```
app/
├── main.py                  # FastAPI entrypoint, lifespan handler, router registration
├── core/
│   ├── config.py            # pydantic-settings (reads .env)
│   ├── database.py          # Async SQLAlchemy engine + session factory
│   ├── security.py          # bcrypt password hashing, JWT encode/decode
│   ├── policy.py            # RBAC permission matrix (ADMIN/FINANCE/STAFF)
│   ├── di.py                # Dependency injection wiring (repos → services)
│   ├── errors.py            # AppError hierarchy + global exception handler
│   ├── middleware.py         # Request-ID + structured logging middleware
│   ├── logging.py           # structlog JSON configuration
│   └── pagination.py        # Generic pagination helpers
└── modules/
    ├── auth/                # Login, logout, JWT, token versioning
    ├── school/              # School profile, user management
    ├── students/            # Student CRUD, CSV bulk import
    ├── fees/                # Fee structures, invoice generation
    ├── payments/            # Payment tracking, reconciliation
    ├── reminders/           # Reminder configuration and history
    ├── reports/             # Overview, outstanding, CSV export
    ├── audit/               # Audit log viewer
    └── zb_bank/             # External bank integration (client, scheduler, reconciliation)
```

### Key Characteristics

- **Framework**: FastAPI 0.115+ with Pydantic v2 and SQLAlchemy 2.0 (full async)
- **Entry point**: `uvicorn app.main:app` (port 8000)
- **Health check**: `GET /health` → `{"status": "ok"}`
- **API docs**: `/docs` (Swagger) and `/redoc`
- **Auth**: JWT (HS256) with bcrypt, role-based (ADMIN, FINANCE, STAFF)
- **Background task**: ZB Bank poller runs as an asyncio task inside the app process (no Celery/Redis)
- **Migrations**: Alembic with async engine support
- **Logging**: structlog with JSON output to stdout
- **Tests**: pytest-asyncio with SQLite test database, 3 test files (auth, students, RBAC)
- **Linting**: ruff + black (configured in pyproject.toml)
- **Python**: 3.11+

### Module Pattern (each module)

```
module/
├── __init__.py
├── models.py       # SQLAlchemy ORM models
├── schemas.py      # Pydantic request/response schemas
├── repository.py   # Data access layer
├── service.py      # Business logic
└── router.py       # FastAPI route handlers
```

---

## 3. Docker Compose and Infrastructure Findings

### Original `docker-compose.yml` (dev only)

The existing compose file contains **only PostgreSQL**:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: class_wallet
      POSTGRES_USER: class_wallet
      POSTGRES_PASSWORD: class_wallet_secret
    ports:
      - "5432:5432"     # Exposed to host — not production-safe
    volumes:
      - pgdata:/var/lib/postgresql/data
```

**Gaps identified:**
- No application container defined
- No Dockerfile existed
- No health checks on the database
- No network isolation
- PostgreSQL port exposed to all interfaces
- No `.dockerignore`
- No reverse proxy
- Hardcoded credentials

### New `docker-compose.prod.yml` (created)

The production compose file adds:
- **App service** with build from Dockerfile, health check, dependency on DB
- **DB service** with health check, restricted port binding (`127.0.0.1` only)
- **Isolated bridge network** (`class-wallet-net`)
- **Environment variable expansion** for credentials (from `.env`)

---

## 4. Required Infrastructure Inventory

### Server Requirements

| Component | Requirement |
|---|---|
| **OS** | Ubuntu 22.04+ / Debian 12+ |
| **CPU** | 2+ vCPUs |
| **RAM** | 2 GB minimum (4 GB recommended) |
| **Disk** | 20 GB+ (OS + Docker images + DB data) |
| **Docker** | Docker Engine 24+ |
| **Compose** | Docker Compose v2 (plugin) |
| **SSH** | OpenSSH server, key-based auth |

### Network Requirements

| Port | Service | Exposure |
|---|---|---|
| 22 | SSH | Public (firewall-restricted) |
| 80 | Nginx (HTTP → redirect) | Public |
| 443 | Nginx (HTTPS → proxy to :8000) | Public |
| 8000 | FastAPI (Uvicorn) | Internal only (via Docker network) |
| 5432 | PostgreSQL | Internal only (127.0.0.1) |

### Application Dependencies

| Service | Details |
|---|---|
| **PostgreSQL 16** | Primary database, persistent volume |
| **Reverse proxy** | Nginx or Caddy for TLS termination |
| **DNS** | A record pointing to server IP |
| **SSL/TLS** | Let's Encrypt via Certbot or Caddy auto-TLS |

### Secrets & Configuration

| Secret | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL async connection string |
| `JWT_SECRET_KEY` | JWT token signing (generate with `openssl rand -hex 32`) |
| `POSTGRES_PASSWORD` | Database password |
| `ZB_BANK_*` credentials | External bank integration (if enabled) |
| `CORS_ORIGINS` | Frontend URLs allowed for CORS |

### Observability (recommended)

- **Logging**: structlog JSON → stdout → Docker logs → optional log aggregator
- **Monitoring**: Health check endpoint at `/health`
- **Metrics**: Consider adding Prometheus endpoint in future

### Backup Requirements

- **PostgreSQL**: Automated `pg_dump` or volume snapshots on a schedule
- **Application**: Git-based (source of truth is the repository)
- **.env file**: Backed up securely outside the server

---

## 5. Recommended GitHub Actions Trigger Strategy

### Trigger Logic

```yaml
on:
  pull_request:
    types: [closed]         # Fires on close events
    branches: [dev]         # Only for PRs targeting dev
    paths: [...]            # Only when relevant files changed
```

Combined with a job-level condition:

```yaml
if: github.event.pull_request.merged == true
```

This two-layer approach ensures:
1. The workflow only runs for the `dev` branch
2. It only runs when relevant paths changed
3. It does **not** run for closed-but-unmerged PRs
4. It does **not** run for pushes, only merged PRs

### Path Filters

```yaml
paths:
  - "app/**"                        # Python application code
  - "scripts/**"                    # Utility scripts
  - "tests/**"                      # Test changes may reveal regressions
  - "alembic/**"                    # Migration files
  - "alembic.ini"                   # Migration config
  - "pyproject.toml"                # Dependency changes
  - "Dockerfile"                    # Container changes
  - "docker-compose*.yml"           # Compose changes
  - ".dockerignore"                 # Build context changes
  - "deploy/**"                     # Deployment scripts
  - ".github/workflows/deploy-dev.yml"  # Pipeline itself
```

### What is excluded (no pipeline trigger)

- `README.md`, `docs/**` — documentation-only changes
- `.claude/` — AI assistant config
- `.vscode/` — IDE settings
- `*.md` files — non-code changes

---

## 6. Recommended Pipeline Stages

```mermaid
graph LR
    A[PR Merged to dev] --> B{Merge gate}
    B --> C[Code Quality]
    B --> D[Tests]
    B --> E[Security Scan]
    B --> F[Docker Validate]
    C --> G[Deploy]
    D --> G
    E --> G
    F --> G
    G --> H[Health Check]
```

### Stage Details

| Stage | What it does | Why |
|---|---|---|
| **check-merge** | Confirms PR was merged (not just closed) | Prevents wasted runs on abandoned PRs |
| **quality** | `ruff check` + `black --check` | Enforces code standards already defined in pyproject.toml |
| **test** | `pytest -v` with SQLite test DB | Catches regressions — tests exist for auth, students, RBAC |
| **security** | `bandit` (SAST) + `pip-audit` (CVE scan) | FastAPI app handles auth/payments — security scanning is essential |
| **docker-validate** | `docker compose config` + `docker build` | Catches Dockerfile/compose errors before deploying |
| **deploy** | SSH → rsync → build → migrate → up | Ships the validated code to the server |
| **health-check** | `curl /health` via SSH | Confirms the deployment actually works |

**Stages run in parallel** where possible (quality, test, security, docker-validate all run concurrently). Deploy only runs after all four pass.

---

## 7. GitHub Actions Workflow File

**File**: `.github/workflows/deploy-dev.yml`

See the workflow file created in the repository. Key design decisions:

1. **Concurrency control** — cancels in-flight runs for the same PR
2. **Parallel CI stages** — quality, test, security, and docker-validate run simultaneously
3. **Environment protection** — deploy job uses `environment: dev` (allows approval gates in GitHub)
4. **SSH with passphrase** — uses `expect` to handle passphrase-protected keys
5. **rsync deployment** — efficient file sync (only changed files transferred)
6. **Sequential deployment** — build → migrate → up → health check
7. **Failure logging** — captures container logs if deployment fails

---

## 8. Required GitHub Secrets and Variables

### Secrets (Settings → Secrets and variables → Actions)

| Secret Name | Purpose | Example |
|---|---|---|
| `SSH_HOST` | Target server IP or hostname | `203.0.113.50` |
| `SSH_USER` | SSH login username | `deploy` |
| `SSH_PRIVATE_KEY` | Full PEM private key | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `SSH_KEY_PASSPHRASE` | Passphrase for the private key | `my-secure-passphrase` |
| `SSH_KNOWN_HOSTS` | Output of `ssh-keyscan $SSH_HOST` | `203.0.113.50 ssh-ed25519 AAAA...` |
| `APP_DIR` | Deployment path on server | `/opt/class-wallet-backend` |
| `ENV_FILE_CONTENT` | Full production `.env` file contents | See `.env.example` for template |

### Variables (non-sensitive, optional)

| Variable Name | Purpose | Default |
|---|---|---|
| `PYTHON_VERSION` | Python version for CI | `3.11` |

### How to generate `SSH_KNOWN_HOSTS`

```bash
ssh-keyscan -H your-server-ip 2>/dev/null
```

Copy the full output into the `SSH_KNOWN_HOSTS` secret.

### How to format `ENV_FILE_CONTENT`

Paste the full `.env` file contents. Example:

```
APP_NAME=ClassWallet
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://class_wallet:STRONG_PASSWORD@db:5432/class_wallet
JWT_SECRET_KEY=<output-of-openssl-rand-hex-32>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=["https://your-frontend-domain.com"]
POSTGRES_DB=class_wallet
POSTGRES_USER=class_wallet
POSTGRES_PASSWORD=STRONG_PASSWORD
ZB_BANK_ENABLED=false
```

**Note**: `DATABASE_URL` uses `db` as the hostname because the app container resolves it via the Docker Compose network.

---

## 9. Remote Server Preparation

### Step-by-step server setup

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 3. Verify Docker Compose v2
docker compose version  # Should be v2.x

# 4. Install rsync (for deployment)
sudo apt install -y rsync curl git

# 5. Create deploy user
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy

# 6. Set up SSH for deploy user
sudo mkdir -p /home/deploy/.ssh
sudo cp ~/.ssh/authorized_keys /home/deploy/.ssh/  # Or add CI public key
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys

# 7. Create application directory
sudo mkdir -p /opt/class-wallet-backend
sudo chown deploy:deploy /opt/class-wallet-backend

# 8. (Optional) Install and configure Nginx
sudo apt install -y nginx certbot python3-certbot-nginx
```

### Nginx reverse proxy config (recommended)

```nginx
# /etc/nginx/sites-available/class-wallet
server {
    listen 80;
    server_name api.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then:

```bash
sudo ln -s /etc/nginx/sites-available/class-wallet /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d api.your-domain.com
```

### Firewall setup

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirect)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### Directory structure on server after first deploy

```
/opt/class-wallet-backend/
├── .env                    # Production environment (written by pipeline)
├── app/                    # Application code (synced by rsync)
├── alembic/                # Migration files
├── alembic.ini
├── scripts/
├── deploy/
│   └── deploy.sh
├── Dockerfile
├── docker-compose.prod.yml
└── pyproject.toml
```

---

## 10. Deployment Flow on the Server

The pipeline executes these steps in order:

```mermaid
sequenceDiagram
    participant GA as GitHub Actions
    participant SRV as Dev Server

    GA->>SRV: 1. rsync — sync repo files
    GA->>SRV: 2. Write .env file (from secret)
    GA->>SRV: 3. Execute deploy/deploy.sh
    Note over SRV: 3a. docker compose build
    Note over SRV: 3b. alembic upgrade head (via run --rm)
    Note over SRV: 3c. docker compose up -d
    Note over SRV: 3d. Health check loop (15 attempts × 4s)
    Note over SRV: 3e. Prune old images
    GA->>SRV: 4. Verify /health returns "ok"
    GA->>SRV: 5. Verify /docs is accessible
```

### Deployment steps in detail

1. **rsync** — Efficiently syncs only changed files, excludes `.git`, `.env`, `*.db`, caches
2. **Write .env** — Pipeline writes the production env file from `ENV_FILE_CONTENT` secret
3. **Build** — `docker compose -f docker-compose.prod.yml build --no-cache`
4. **Migrate** — Runs Alembic migrations in a temporary container (`run --rm`)
5. **Start** — `docker compose up -d --remove-orphans` — recreates only changed services
6. **Health check** — Polls `http://localhost:8000/health` up to 15 times (60s total)
7. **Prune** — Removes dangling Docker images to reclaim disk space

---

## 11. Post-Deploy Verification and Rollback

### Health checks performed

1. **Docker-level**: Container HEALTHCHECK (curl to /health every 30s)
2. **Pipeline-level**: SSH → curl /health (with timeout)
3. **Smoke test**: SSH → curl /docs (verifies FastAPI is fully up)

### Rollback procedure

If deployment fails, the pipeline logs container output. To manually roll back:

```bash
# On the server:
cd /opt/class-wallet-backend

# Option 1: Revert to previous git state
git log --oneline -5          # Find the last good commit
git checkout <good-commit>
docker compose -f docker-compose.prod.yml up -d --build

# Option 2: Use Docker's previous image layers
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d  # Uses cached layers

# Option 3: Revert the PR in GitHub and merge to dev
# (triggers a new deployment with the reverted code)
```

### Database rollback

```bash
# Downgrade one migration step
docker compose -f docker-compose.prod.yml run --rm app alembic downgrade -1
```

---

## 12. Risks and Gaps

### Critical gaps in the current repository

| Gap | Impact | Recommendation |
|---|---|---|
| **No Dockerfile existed** | Cannot containerize the app | ✅ Created in this PR |
| **No production compose** | No app service defined | ✅ Created `docker-compose.prod.yml` |
| **No `.dockerignore`** | Build context includes unnecessary files | ✅ Created |
| **No deployment script** | No automated deploy process | ✅ Created `deploy/deploy.sh` |
| **SQLite as default DB** | Not suitable for production | Use PostgreSQL via `DATABASE_URL` env |
| **JWT secret has default** | Insecure if not overridden | Must set `JWT_SECRET_KEY` in production |
| **No rate limiting** | `/auth/login` vulnerable to brute force | Add `slowapi` or `fastapi-limiter` |
| **No HTTPS in app** | TLS must be handled externally | Nginx/Caddy reverse proxy required |
| **No log aggregation** | Logs only in Docker | Consider forwarding to a log service |
| **No DB backups** | Data loss risk | Set up `pg_dump` cron or volume snapshots |
| **`asyncpg` not in deps** | PostgreSQL driver missing from pyproject.toml | Add `asyncpg` to dependencies |

### Deployment risks

| Risk | Mitigation |
|---|---|
| Database migration failure | Migrations run before service swap; failure aborts deploy |
| SSH key compromise | Key is passphrase-protected; stored in GitHub Secrets |
| .env exposure | Written with `chmod 600`; excluded from rsync and git |
| Downtime during deploy | Brief (seconds) during container restart; consider blue-green for zero-downtime |
| Disk space | Old images pruned automatically; monitor disk usage |

---

## 13. Exact Files Created or Modified

### New files created

| File | Purpose |
|---|---|
| `Dockerfile` | Multi-stage Docker build for the FastAPI app |
| `docker-compose.prod.yml` | Production Compose with app + db + health checks |
| `.dockerignore` | Excludes unnecessary files from Docker build |
| `.github/workflows/deploy-dev.yml` | Full CI/CD pipeline |
| `deploy/deploy.sh` | Server-side deployment script |
| `docs/ci-cd-pipeline.md` | This document |

### Files that should be modified

| File | Change needed |
|---|---|
| `pyproject.toml` | Add `asyncpg` to production dependencies |
| `.env.example` | Add `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |

---

## 14. Final Recommendation

### 1. Best overall pipeline approach

A **single-file GitHub Actions workflow** with parallel CI stages and a gated deployment stage. The pipeline is self-contained and easy to maintain. No external CI services or registries needed.

### 2. Exact trigger approach

```yaml
on:
  pull_request:
    types: [closed]
    branches: [dev]
    paths: [app/**, tests/**, alembic/**, Dockerfile, docker-compose*.yml, ...]

jobs:
  check-merge:
    if: github.event.pull_request.merged == true
```

This guarantees: merged only, dev only, relevant files only.

### 3. Safest deployment model

**rsync + Docker Compose on the server**. This approach:
- Doesn't require a container registry
- Uses the repo as the single source of truth
- Supports migration-before-swap
- Provides automatic health checks
- Allows easy manual rollback via git

### 4. First change to make

1. **Add `asyncpg` to `pyproject.toml` dependencies** — required for PostgreSQL in production
2. **Create a `dev` branch** in your repository
3. **Set up GitHub Secrets** (SSH_HOST, SSH_USER, SSH_PRIVATE_KEY, SSH_KEY_PASSPHRASE, SSH_KNOWN_HOSTS, APP_DIR, ENV_FILE_CONTENT)
4. **Prepare the target server** (Docker, deploy user, app directory)
5. **Open a PR to `dev`** with all the new files and test the pipeline

```bash
# Add asyncpg dependency
# In pyproject.toml, add to dependencies:
#   "asyncpg>=0.29.0",

# Create dev branch
git checkout -b dev
git add .
git commit -m "Add CI/CD pipeline and Docker infrastructure"
git push -u origin dev
```

---

## Appendix: Pipeline Architecture Diagram

```mermaid
flowchart TB
    subgraph "GitHub"
        PR[PR merged to dev] --> Gate{Merged?}
        Gate -->|No| Skip[Skip — no deploy]
        Gate -->|Yes| Parallel

        subgraph Parallel["Parallel CI Stages"]
            Q[Code Quality<br>ruff + black]
            T[Tests<br>pytest]
            S[Security<br>bandit + pip-audit]
            D[Docker Validate<br>compose config + build]
        end

        Parallel --> Deploy[Deploy via SSH]
    end

    subgraph "Dev Server"
        Deploy --> Rsync[rsync files]
        Rsync --> Env[Write .env]
        Env --> Build[docker compose build]
        Build --> Migrate[alembic upgrade head]
        Migrate --> Up[docker compose up -d]
        Up --> Health[Health check loop]

        subgraph Services["Running Services"]
            API[FastAPI :8000]
            DB[(PostgreSQL :5432)]
            Nginx[Nginx :443]
        end

        Health --> Services
    end
```
