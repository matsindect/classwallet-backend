"""FastAPI application entrypoint for the Class Wallet backend.

Configures the application instance with CORS middleware, request-ID
middleware, a centralised exception handler, and registers all module
routers (auth, school, students, fees, payments, reminders, reports,
audit).  Also starts the ZB Bank background poller via the lifespan
handler and exposes a lightweight ``/health`` endpoint.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import AppError, app_error_handler
from app.core.logging import setup_logging
from app.core.middleware import RequestIdMiddleware
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.fees.router import router as fees_router
from app.modules.payments.router import router as payments_router
from app.modules.reminders.router import router as reminders_router
from app.modules.reports.router import router as reports_router
from app.modules.school.router import router as school_router
from app.modules.students.router import router as students_router
from app.modules.zb_bank.scheduler import start_zb_bank_poller

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.

    Starts the ZB Bank background poller on startup and cancels it
    on shutdown.
    """
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)

# --- Exception handlers ---
app.add_exception_handler(AppError, app_error_handler)

# --- Routers ---
app.include_router(auth_router)
app.include_router(school_router)
app.include_router(students_router)
app.include_router(fees_router)
app.include_router(payments_router)
app.include_router(reminders_router)
app.include_router(reports_router)
app.include_router(audit_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Return a simple health-check response.

    Returns:
        dict: A JSON object with ``{"status": "ok"}``.
    """
    return {"status": "ok"}
