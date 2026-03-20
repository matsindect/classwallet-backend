"""Background scheduler for ZB Bank transaction polling and reconciliation.

Runs as an asyncio background task within the FastAPI application lifespan.
Periodically polls pending payments from ZB Bank for each registered school,
stores new transactions, and auto-reconciles them against outstanding invoices.

The poller waits for an ``asyncio.Event`` (``app_ready``) to be set by the
lifespan handler, ensuring it only starts polling **after** the application
(including migrations) has fully started.

Controlled by two settings:
- ``ZB_BANK_ENABLED``: Master switch (default ``False``).
- ``ZB_BANK_POLL_INTERVAL_SECONDS``: Polling frequency (default 300s / 5 min).
"""

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.modules.school.models import School
from app.modules.zb_bank.client import ZBBankClient
from app.modules.zb_bank.service import ZBBankService

logger = get_logger(__name__)

# Set by the lifespan handler once the app is fully started.
app_ready = asyncio.Event()


async def _get_all_school_ids() -> list[str]:
    """Fetch all school IDs from the database.

    Returns:
        A list of school UUID strings.
    """
    async with async_session_factory() as session:
        result = await session.execute(select(School.id))
        return [row[0] for row in result.all()]


async def _run_poll_cycle() -> None:
    """Execute one poll-and-reconcile cycle for all schools.

    Creates a fresh database session and ZBBankService for each school,
    ensuring transaction isolation. Errors for individual schools are
    logged but do not halt processing of other schools.
    """
    school_ids = await _get_all_school_ids()
    if not school_ids:
        logger.debug("zb_bank_scheduler_no_schools")
        return

    client = ZBBankClient()

    for school_id in school_ids:
        async with async_session_factory() as session:
            try:
                service = ZBBankService(session=session, client=client)
                result = await service.poll_and_reconcile(school_id)
                await session.commit()

                poll = result["poll"]
                recon = result["reconciliation"]
                logger.info(
                    "zb_bank_cycle_school_complete",
                    school_id=school_id,
                    fetched=poll["total_fetched"],
                    new=poll["new_stored"],
                    matched=recon["matched_count"],
                    unmatched=recon["unmatched_count"],
                    reconciled_amount=recon["total_amount_reconciled"],
                )
            except Exception:
                await session.rollback()
                logger.exception(
                    "zb_bank_cycle_school_error",
                    school_id=school_id,
                )


async def start_zb_bank_poller() -> None:
    """Start the background polling loop.

    Runs indefinitely, executing a poll-and-reconcile cycle at the
    configured interval. Only starts if ``ZB_BANK_ENABLED`` is True
    and ``ZB_BANK_INSTITUTION_ID`` is configured.

    This function is designed to be launched as a background asyncio task
    from the FastAPI lifespan handler.
    """
    if not settings.ZB_BANK_ENABLED:
        logger.info("zb_bank_poller_disabled")
        return

    if not settings.ZB_BANK_INSTITUTION_ID:
        logger.warning("zb_bank_poller_no_credentials", msg="ZB_BANK_INSTITUTION_ID not set")
        return

    interval = settings.ZB_BANK_POLL_INTERVAL_SECONDS

    # Wait until the lifespan handler signals the app is fully ready.
    logger.info("zb_bank_poller_waiting_for_app_ready")
    await app_ready.wait()

    logger.info(
        "zb_bank_poller_started",
        interval_seconds=interval,
    )

    while True:
        try:
            await _run_poll_cycle()
        except Exception:
            logger.exception("zb_bank_poll_cycle_error")

        await asyncio.sleep(interval)
