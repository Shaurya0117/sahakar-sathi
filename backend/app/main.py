"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000
"""
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
        "services. Built for SIH 2026."
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

# ── Register routers ──────────────────────────────────────────────────────────
app.include_router(api_router)

import os
from fastapi.staticfiles import StaticFiles
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
