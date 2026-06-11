"""
Auth tests.
Uses an in-memory SQLite database so tests never touch production PostgreSQL.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import User  # noqa: ensure models registered
from app.core.security import hash_password
import uuid

# ── In-memory test database ───────────────────────────────────────────────────
TEST_DB_URL = "sqlite:///./test_auth.db"

engine_test = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test, drop after."""
    Base.metadata.create_all(bind=engine_test)
    # Seed a system admin so register endpoint works (requires ROLE_SYSTEM_ADMIN)
    db = TestingSession()
    existing = db.query(User).filter(User.username == "sysadmin").first()
    if not existing:
        db.add(User(
            id=str(uuid.uuid4()),
            username="sysadmin",
            email="sysadmin@test.com",
            hashed_password=hash_password("Admin1234!"),
            full_name="System Admin",
            role="ROLE_SYSTEM_ADMIN",
            county="Nairobi",
            is_active=True,
        ))
        db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine_test)


client = TestClient(app)


def get_admin_token():
    res = client.post("/api/v1/auth/login", json={
        "username": "sysadmin",
        "password": "Admin1234!",
    })
    return res.json().get("token", "")


def test_register_and_login():
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Register a new trainer — password meets all strength requirements
    res = client.post("/api/v1/auth/register", json={
        "username":  "testtrainer",
        "email":     "trainer@test.com",
        "password":  "Trainer1234!",   # uppercase + number + special char
        "full_name": "Test Trainer",
        "role":      "ROLE_TRAINER",
        "county":    "Nairobi",
    }, headers=headers)
    assert res.status_code == 201, res.json()
    assert res.json()["username"] == "testtrainer"

    # Login with the new account
    res = client.post("/api/v1/auth/login", json={
        "username": "testtrainer",
        "password": "Trainer1234!",
    })
    assert res.status_code == 200, res.json()
    assert "token" in res.json()
    assert res.json()["role"] == "ROLE_TRAINER"


def test_login_wrong_password():
    res = client.post("/api/v1/auth/login", json={
        "username": "sysadmin",
        "password": "wrongpassword",
    })
    assert res.status_code == 401


def test_login_nonexistent_user():
    res = client.post("/api/v1/auth/login", json={
        "username": "nobody",
        "password": "Whatever1!",
    })
    assert res.status_code == 401


def test_weak_password_rejected():
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post("/api/v1/auth/register", json={
        "username":  "weakuser",
        "email":     "weak@test.com",
        "password":  "test1234",   # no uppercase, no special char
        "full_name": "Weak User",
        "role":      "ROLE_TRAINER",
        "county":    "Nairobi",
    }, headers=headers)
    assert res.status_code == 400
    assert "Password must contain" in res.json()["detail"]


def test_duplicate_username_rejected():
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "username":  "dupuser",
        "email":     "dup@test.com",
        "password":  "Secure1234!",
        "full_name": "Dup User",
        "role":      "ROLE_TRAINER",
        "county":    "Nairobi",
    }
    res1 = client.post("/api/v1/auth/register", json=payload, headers=headers)
    assert res1.status_code == 201
    res2 = client.post("/api/v1/auth/register", json=payload, headers=headers)
    assert res2.status_code == 409