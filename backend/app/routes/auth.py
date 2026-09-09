"""
Authentication routes.

Thin handlers — validation and business logic live in schemas and services.

Endpoints:
    POST /api/auth/register     — create customer or worker account
    POST /api/auth/login        — obtain JWT
    GET  /api/auth/me           — current user info (requires JWT)
    GET  /api/auth/admin-test   — verify ADMIN role enforcement
    GET  /api/auth/worker-test  — verify WORKER role enforcement
    GET  /api/auth/customer-test — verify CUSTOMER role enforcement
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    require_admin,
    require_customer,
    require_worker,
)
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import LoginResponse, RegisterResponse
from app.schemas.user import UserRegisterRequest, UserResponse
from app.services.auth import authenticate_user, build_token_for_user, create_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ── POST /api/auth/register ────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new customer or worker",
)
def register(data: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Create a new user account.

    - Only CUSTOMER and WORKER roles are allowed via self-registration.
    - ADMIN accounts must be seeded via the seed_admin script.
    - Duplicate email returns HTTP 409.
    """
    try:
        user = create_user(db, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return RegisterResponse(
        message="Account created successfully",
        user=UserResponse.model_validate(user),
    )


# ── POST /api/auth/login ───────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login and obtain JWT",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authenticate with email (username field) + password.

    Returns a bearer JWT and safe user information.
    Uses OAuth2PasswordRequestForm so the /docs UI works out of the box.
    """
    user = authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = build_token_for_user(user)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ── GET /api/auth/me ───────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
def me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


# ── Role-verification test endpoints (dev only) ────────────────────────────────

@router.get("/admin-test", summary="[Dev] Verify ADMIN role enforcement")
def admin_test(current_user: User = Depends(require_admin)):
    return {"ok": True, "role": current_user.role, "user": current_user.email}


@router.get("/worker-test", summary="[Dev] Verify WORKER role enforcement")
def worker_test(current_user: User = Depends(require_worker)):
    return {"ok": True, "role": current_user.role, "user": current_user.email}


@router.get("/customer-test", summary="[Dev] Verify CUSTOMER role enforcement")
def customer_test(current_user: User = Depends(require_customer)):
    return {"ok": True, "role": current_user.role, "user": current_user.email}
