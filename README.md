# Class Wallet Backend

Production-grade Python API server for school fee management. Built with FastAPI, SQLAlchemy 2.0, Pydantic v2, and JWT authentication.

## Quick Start

```bash
# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Seed dev data
python -m scripts.seed

# Start server
uvicorn app.main:app --reload --port 8000
```

**Seed credentials:**
- Admin: `admin@greenfield.edu` / `admin123`
- Finance: `finance@greenfield.edu` / `finance123`
- Staff: `staff@greenfield.edu` / `staff123`

## Running Tests

```bash
pytest -v
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
app/
  core/           # Config, DB, security, errors, pagination, DI, middleware
  modules/
    auth/         # Login, logout, token management
    school/       # School profile, user management
    students/     # Student CRUD, CSV import
    fees/         # Fee structures, invoice generation
    payments/     # Payment tracking, reconciliation
    reminders/    # Reminder config and history
    reports/      # Overview, outstanding, CSV export
    audit/        # Audit log viewer
  main.py         # FastAPI app entrypoint
alembic/          # Database migrations
tests/            # pytest test suite
scripts/          # Seed script
```

## Environment Variables

Copy `.env.example` to `.env` and adjust values. Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | sqlite+aiosqlite:///./class_wallet.db | Database connection string |
| JWT_SECRET_KEY | change-me... | Secret for JWT signing |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | 60 | Token lifetime |
| CORS_ORIGINS | ["http://localhost:3000"] | Allowed CORS origins |

For PostgreSQL, use: `postgresql+asyncpg://user:pass@localhost:5432/class_wallet`

## Docker (PostgreSQL)

```bash
docker-compose up -d
# Update DATABASE_URL in .env to point to PostgreSQL
```

## Security Notes

- Passwords hashed with bcrypt via passlib
- JWT tokens with rotating token_version for logout invalidation
- Role-based access control: ADMIN, FINANCE, STAFF
- CORS configured via environment
- **Brute-force mitigation**: Consider adding `slowapi` or `fastapi-limiter` for rate limiting on `/auth/login` in production
