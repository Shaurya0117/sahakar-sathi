"""
Authentication business logic.

All DB interactions for auth live here.
Route handlers call these functions — they do not touch the DB directly.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.auth.password import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserRegisterRequest


# ── Registration ───────────────────────────────────────────────────────────────

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Return a User by email or None."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Return a User by primary key or None."""
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, data: UserRegisterRequest) -> User:
    """
    Create a new user.

    :raises ValueError: if the email is already registered.
    """
    if get_user_by_email(db, data.email):
        raise ValueError("A user with this email already exists")

    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        role=data.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── Login ──────────────────────────────────────────────────────────────────────

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Verify email + password.

    Returns the User if credentials are correct and the account is active,
    otherwise returns None.
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def build_token_for_user(user: User) -> str:
    """Create a JWT for *user* using their id and role."""
    return create_access_token(subject=str(user.id), role=user.role.value)


# ── Seeding (used by seed_admin script) ───────────────────────────────────────

def create_admin_if_absent(db: Session, name: str, email: str, password: str) -> User:
    """
    Create an ADMIN user if no user with *email* exists.
    Used by the seed_admin script only — not exposed via API.
    """
    existing = get_user_by_email(db, email)
    if existing:
        return existing

    admin = User(
        name=name,
        email=email,
        phone=None,
        password_hash=hash_password(password),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin
