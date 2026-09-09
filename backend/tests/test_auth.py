"""
Authentication tests — 12 required cases + 1 bonus.

Fixtures and DB override are provided by conftest.py.

Run:
    cd backend
    pytest tests/test_auth.py -v
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────────────

def register_customer(email="customer@test.com", password="Password1"):
    return client.post("/api/auth/register", json={
        "name": "Test Customer",
        "email": email,
        "password": password,
        "role": "CUSTOMER",
    })


def register_worker(email="worker@test.com", password="Password1"):
    return client.post("/api/auth/register", json={
        "name": "Test Worker",
        "email": email,
        "password": password,
        "role": "WORKER",
    })


def login(email, password="Password1"):
    return client.post("/api/auth/login", data={
        "username": email,
        "password": password,
    })


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_register_customer():
    """1. Register a customer successfully."""
    res = register_customer()
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["user"]["role"] == "CUSTOMER"
    assert data["user"]["email"] == "customer@test.com"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


def test_register_worker():
    """2. Register a worker successfully."""
    res = register_worker()
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["user"]["role"] == "WORKER"


def test_duplicate_email_rejected():
    """3. Registering with an already-used email returns 409."""
    register_customer()
    res = register_customer()  # same email
    assert res.status_code == 409, res.text


def test_password_is_hashed():
    """4. The stored password_hash is not the plain-text password."""
    from tests.conftest import TestingSessionLocal
    from app.services.auth import get_user_by_email
    from app.auth.password import verify_password

    register_customer(email="hash@test.com", password="MySecret1")

    db = TestingSessionLocal()
    user = get_user_by_email(db, "hash@test.com")
    db.close()

    assert user is not None
    assert user.password_hash != "MySecret1"
    assert verify_password("MySecret1", user.password_hash) is True


def test_login_succeeds():
    """5. Valid credentials return a JWT and user info."""
    register_customer()
    res = login("customer@test.com")
    assert res.status_code == 200, res.text
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "customer@test.com"


def test_incorrect_password_rejected():
    """6. Wrong password returns 401."""
    register_customer()
    res = login("customer@test.com", password="WrongPass")
    assert res.status_code == 401, res.text


def test_inactive_user_rejected():
    """7. A deactivated user cannot log in."""
    from tests.conftest import TestingSessionLocal
    from app.services.auth import get_user_by_email

    register_customer(email="inactive@test.com")

    db = TestingSessionLocal()
    user = get_user_by_email(db, "inactive@test.com")
    assert user is not None
    user.is_active = False
    db.commit()
    db.close()

    res = login("inactive@test.com")
    assert res.status_code == 401, res.text


def test_me_with_valid_jwt():
    """8. /me returns user info when a valid JWT is provided."""
    register_customer()
    token_res = login("customer@test.com")
    assert token_res.status_code == 200, token_res.text
    token = token_res.json()["access_token"]

    res = client.get("/api/auth/me", headers=auth_header(token))
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["email"] == "customer@test.com"
    assert "password_hash" not in data


def test_me_without_jwt():
    """9. /me returns 401 when no token is provided."""
    res = client.get("/api/auth/me")
    assert res.status_code == 401, res.text


def test_admin_authorization():
    """10. Admin seeded via service can access /admin-test."""
    from tests.conftest import TestingSessionLocal
    from app.services.auth import create_admin_if_absent

    db = TestingSessionLocal()
    create_admin_if_absent(db, "Admin", "admin@test.com", "AdminPass1")
    db.close()

    res = login("admin@test.com", password="AdminPass1")
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]

    admin_res = client.get("/api/auth/admin-test", headers=auth_header(token))
    assert admin_res.status_code == 200, admin_res.text


def test_worker_cannot_access_admin_endpoint():
    """11. Worker token is rejected by /admin-test with 403."""
    register_worker()
    login_res = login("worker@test.com")
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]

    res = client.get("/api/auth/admin-test", headers=auth_header(token))
    assert res.status_code == 403, res.text


def test_customer_cannot_access_admin_endpoint():
    """12. Customer token is rejected by /admin-test with 403."""
    register_customer()
    login_res = login("customer@test.com")
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]

    res = client.get("/api/auth/admin-test", headers=auth_header(token))
    assert res.status_code == 403, res.text


def test_admin_cannot_self_register():
    """Bonus: ADMIN role is blocked via the registration endpoint (422 from Pydantic)."""
    res = client.post("/api/auth/register", json={
        "name": "Sneaky Admin",
        "email": "sneaky@test.com",
        "password": "Password1",
        "role": "ADMIN",
    })
    assert res.status_code == 422, res.text
