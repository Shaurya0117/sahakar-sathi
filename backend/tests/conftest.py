"""
conftest.py — shared pytest fixtures and DB override.

Both test_auth.py and test_workers.py use the same in-memory SQLite engine
via StaticPool. Having this in conftest ensures all test modules share ONE
engine and the same dependency override, so table drops in one file don't
break tests in another.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import app

# ── Shared in-memory SQLite ────────────────────────────────────────────────────
engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Register the override on import — applies to all tests that use app
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_database():
    """Drop and recreate all tables before each individual test."""
    Base.metadata.drop_all(bind=engine_test)
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


# Expose the testing session and client for tests that need them
@pytest.fixture
def db():
    """Provide a DB session for direct service-layer calls in tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)
