"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routes import api_router

# ── Create all tables declared via SQLAlchemy models ──────────────────────────
# Models must be imported before this line so Base.metadata knows about them.
import app.models  # noqa: F401 — side-effect import registers models

Base.metadata.create_all(bind=engine)

# ── Build the FastAPI app ─────────────────────────────────────────────────────
app = FastAPI(
    title="Cooperative Gig Services Platform",
    description=(
        "A cooperative-owned digital marketplace for household and community "
        "services. Developed as an academic Mini Project."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow the Vite dev server (port 5173) during development.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup Events ────────────────────────────────────────────────────────────
def check_production_secrets():
    """Ensure sensitive secrets are non-default and non-empty in production."""
    if settings.APP_ENV == "production":
        dev_defaults = {
            "change-me",
            "dev-change-me-before-deploy",
            "dev-secret-key-for-simulations",
            "test-secret-key-for-ml-tests",
            "secret",
            "",
        }
        if not settings.SECRET_KEY or settings.SECRET_KEY.strip() in dev_defaults:
            raise RuntimeError("Fatal: In production, SECRET_KEY must be set to a secure, non-default value.")
        if not settings.PROOF_SECRET or settings.PROOF_SECRET.strip() in dev_defaults:
            raise RuntimeError("Fatal: In production, PROOF_SECRET must be set to a secure, non-default value.")


@app.on_event("startup")
def startup_event():
    check_production_secrets()
    if settings.PROOF_SECRET == "dev-change-me-before-deploy":
        logging.warning("WARNING: PROOF_SECRET is set to the default dev value 'dev-change-me-before-deploy'. Please change this in production.")
    try:
        from scripts.migrate_proof_columns import run_migration
        run_migration()
    except Exception as e:
        logging.warning(f"Could not run proof migration at startup: {e}")

# ── Register routers ──────────────────────────────────────────────────────────
app.include_router(api_router)

import os
from fastapi.staticfiles import StaticFiles
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
