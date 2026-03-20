"""Password hashing and JWT token utilities.

Wraps ``passlib`` (bcrypt) for password hashing/verification and
``python-jose`` for creating and decoding JSON Web Tokens.  All
cryptographic parameters (secret key, algorithm, expiry) are sourced from
the application ``settings`` singleton.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Args:
        password: The plain-text password to hash.

    Returns:
        The bcrypt hash string.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash.

    Args:
        plain_password: The plain-text password provided by the user.
        hashed_password: The bcrypt hash to compare against.

    Returns:
        ``True`` if the password matches the hash, ``False`` otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The token subject claim (``sub``), typically a user ID.
        expires_delta: Optional custom lifetime for the token.  When
            ``None``, defaults to ``settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES``.

    Returns:
        An encoded JWT string.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decode and verify a JWT access token.

    Args:
        token: The encoded JWT string.

    Returns:
        The decoded payload as a dictionary if the token is valid, or
        ``None`` if verification fails (expired, tampered, etc.).
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None
