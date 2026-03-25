"""FastAPI application entrypoint for the Class Wallet backend.

Configures the application instance with CORS middleware, request-ID
middleware, a centralised exception handler, and registers all module
routers (auth, school, students, fees, payments, reminders, reports,
audit).  Also starts the ZB Bank background poller via the lifespan
handler and exposes a lightweight ``/health`` endpoint.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from app.core.config import settings
from app.core.cors import add_cors_middleware
from app.core.errors import AppError, app_error_handler, unhandled_error_handler
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestIdMiddleware
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.fees.router import router as fees_router
from app.modules.payments.router import router as payments_router
from app.modules.rbac.router import router as rbac_router
from app.modules.reminders.router import router as reminders_router
from app.modules.reports.router import router as reports_router
from app.modules.school.router import router as school_router
from app.modules.schools.router import router as schools_router
from app.modules.students.router import router as students_router
from app.modules.zb_bank.router import router as zb_bank_router
from app.modules.zb_bank.scheduler import start_zb_bank_poller

setup_logging()
logger = get_logger(__name__)


async def _run_migrations() -> None:
    """Run Alembic migrations programmatically at startup."""
    from alembic.config import Config

    from alembic import command
    from app.core.database import engine

    alembic_cfg = Config("alembic.ini")

    def _upgrade(connection):
        alembic_cfg.attributes["connection"] = connection
        command.upgrade(alembic_cfg, "head")

    async with engine.begin() as conn:
        await conn.run_sync(_upgrade)

    logger.info("migrations_applied")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Runs database migrations first, then starts the ZB Bank background
    poller. On shutdown the poller task is cancelled cleanly.
    """
    await _run_migrations()

    zb_task = asyncio.create_task(start_zb_bank_poller())
    yield
    zb_task.cancel()
    try:
        await zb_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# --- Middleware ---
add_cors_middleware(app)
app.add_middleware(RequestIdMiddleware)

# --- Exception handlers ---
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)


# --- Health check (no prefix — used by Docker/Nginx) ---
@app.get("/health", tags=["Health"])
async def health_check():
    """Return a simple health-check response."""
    return {"status": "ok"}


# --- Versioned API router ---
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(school_router)
api_router.include_router(students_router)
api_router.include_router(fees_router)
api_router.include_router(payments_router)
api_router.include_router(reminders_router)
api_router.include_router(reports_router)
api_router.include_router(audit_router)
api_router.include_router(rbac_router)
api_router.include_router(schools_router)
api_router.include_router(zb_bank_router)

app.include_router(api_router)
