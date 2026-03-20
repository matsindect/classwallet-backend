"""Structured JSON logging configuration using structlog.

Call ``setup_logging()`` once during application startup to configure
structlog's global processor chain.  Subsequent calls to ``get_logger()``
return a bound logger that emits structured JSON to stdout.
"""

import logging
import sys

import structlog


def setup_logging() -> None:
    """Configure structlog's global processor chain for JSON logging.

    Should be called once during application startup (e.g. in a ``lifespan``
    handler).  Subsequent ``structlog.get_logger()`` calls will inherit this
    configuration.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger with the given name.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        A ``BoundLogger`` that emits structured JSON to stdout.
    """
    return structlog.get_logger(name)
