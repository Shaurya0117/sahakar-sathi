"""
Password hashing utilities using passlib + bcrypt.

Usage:
    from app.auth.password import hash_password, verify_password

Never store or compare plain-text passwords.
"""
import bcrypt
if not hasattr(bcrypt, "__about__"):
    class About:
        __version__ = "4.0.0"
    bcrypt.__about__ = About

from passlib.context import CryptContext

# bcrypt is the recommended algorithm — slow enough to resist brute-force
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the bcrypt *hashed* value."""
    return _pwd_context.verify(plain, hashed)
