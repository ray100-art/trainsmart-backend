"""Shared test configuration — must set env before app imports."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_trainsmart.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters-long")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("EMAIL_ENABLED", "False")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import User, AuditLog, LegacyCertificate, TrainingProgram  # noqa: F401 — ensure all tables are registered
from app.core.security import hash_password
import uuid

TEST_DB_URL = os.environ["DATABASE_URL"]

engine_test = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    db = TestingSession()
    for user_data in [
        dict(id=str(uuid.uuid4()), username="sysadmin", email="admin@test.com",
             hashed_password=hash_password("Admin1234!"), full_name="Admin",
             role="ROLE_SYSTEM_ADMIN", county="Nairobi", is_active=True, token_version=0),
        dict(id=str(uuid.uuid4()), username="trainer1", email="trainer@test.com",
             hashed_password=hash_password("Trainer1234!"), full_name="Trainer One",
             role="ROLE_TRAINER", county="Nairobi", is_active=True, token_version=0),
        dict(id=str(uuid.uuid4()), username="trainer2", email="trainer2@test.com",
             hashed_password=hash_password("Trainer5678!"), full_name="Trainer Two",
             role="ROLE_TRAINER", county="Mombasa", is_active=True, token_version=0),
        dict(id=str(uuid.uuid4()), username="county1", email="county@test.com",
             hashed_password=hash_password("County1234!"), full_name="County Officer",
             role="ROLE_COUNTY_OFFICER", county="Nairobi", is_active=True, token_version=0),
        dict(id=str(uuid.uuid4()), username="county2", email="county2@test.com",
             hashed_password=hash_password("County5678!"), full_name="Mombasa Officer",
             role="ROLE_COUNTY_OFFICER", county="Mombasa", is_active=True, token_version=0),
        dict(id=str(uuid.uuid4()), username="natadmin", email="nat@test.com",
             hashed_password=hash_password("NatAdmin1!"), full_name="National Admin",
             role="ROLE_NATIONAL_ADMIN", county="Nairobi", is_active=True, token_version=0),
    ]:
        if not db.query(User).filter(User.username == user_data["username"]).first():
            db.add(User(**user_data))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine_test)


def get_token(client: TestClient, username: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.json()}"
    return res.json()["token"]


def auth_headers(client: TestClient, username: str, password: str) -> dict:
    """Return Authorization headers; login also sets httpOnly cookie on the client."""
    token = get_token(client, username, password)
    return {"Authorization": f"Bearer {token}"}
