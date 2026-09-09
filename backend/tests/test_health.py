"""
Tests for GET /api/health.

Run:
    cd backend
    pytest tests/test_health.py -v
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    """Health endpoint must return HTTP 200."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_returns_ok():
    """Health endpoint body must contain status: ok."""
    response = client.get("/api/health")
    data = response.json()
    assert data == {"status": "ok"}
