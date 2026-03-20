"""Application configuration loaded from environment variables.

Uses pydantic-settings to read values from a ``.env`` file or the process
environment.  A single ``settings`` instance is created at module level and
imported throughout the application.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the ClassWallet backend.

    All values can be overridden by setting the corresponding environment
    variable (case-insensitive).  A ``.env`` file in the project root is
    loaded automatically; unknown keys are silently ignored.

    Attributes:
        APP_NAME: Display name of the application.
        APP_ENV: Current deployment environment (e.g. ``"development"``,
            ``"production"``).
        DEBUG: When ``True``, enables verbose SQL logging and other debug
            helpers.
        DATABASE_URL: Async SQLAlchemy database connection string.
        JWT_SECRET_KEY: Secret used to sign and verify JWT access tokens.
        JWT_ALGORITHM: Algorithm used for JWT encoding (default ``"HS256"``).
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES: Lifetime of an access token in
            minutes.
        CORS_ORIGINS: List of allowed origins for CORS requests.
        MAX_PAGE_SIZE: Upper bound for the ``page_size`` query parameter.
        DEFAULT_PAGE_SIZE: Page size used when the client does not specify one.
    """

    APP_NAME: str = "ClassWallet"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite+aiosqlite:///./class_wallet.db"

    JWT_SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Accept both JSON array and comma-separated string formats."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Try JSON first, fall back to comma-separated
            if v.startswith("["):
                import json

                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    MAX_PAGE_SIZE: int = 100
    DEFAULT_PAGE_SIZE: int = 20

    # ZB Bank integration
    ZB_BANK_BASE_URL: str = "https://zbnet.zb.co.zw"
    ZB_BANK_INSTITUTION_ID: str = ""
    ZB_BANK_PASSWORD: str = ""
    ZB_BANK_BILLER_ID: str = ""
    ZB_BANK_TIMEOUT_SECONDS: int = 30
    ZB_BANK_POLL_INTERVAL_SECONDS: int = 300  # 5 minutes default
    ZB_BANK_ENABLED: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
