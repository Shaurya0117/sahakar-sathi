"""
JWT creation and decoding.

Tokens contain:
    sub  — str(user.id)
    role — UserRole value
    exp  — expiration timestamp

The SECRET_KEY and ALGORITHM are read from app.config.settings.
Never hardcode secrets here.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.config import settings


def create_access_token(subject: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT.

    :param subject: str representation of the user's primary key.
    :param role: UserRole enum value (string).
    :param expires_delta: override default expiry.
    :returns: encoded JWT string.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT.

    :raises JWTError: if the token is invalid or expired.
    :returns: decoded payload dict.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
