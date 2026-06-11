"""
Certificate tests.
Uses an in-memory SQLite database so tests never touch production PostgreSQL.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import User  # noqa
from app.core.security import hash_password
import uuid

TEST_DB_URL = "sqlite:///./test_certs.db"

engine_test = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    db = TestingSession()
    for user_data in [
        dict(id=str(uuid.uuid4()), username="sysadmin", email="admin@test.com",
             hashed_password=hash_password("Admin1234!"), full_name="Admin",
             role="ROLE_SYSTEM_ADMIN", county="Nairobi", is_active=True),
        dict(id=str(uuid.uuid4()), username="trainer1", email="trainer@test.com",
             hashed_password=hash_password("Trainer1234!"), full_name="Trainer One",
             role="ROLE_TRAINER", county="Nairobi", is_active=True),
        dict(id=str(uuid.uuid4()), username="natadmin", email="nat@test.com",
             hashed_password=hash_password("NatAdmin1!"), full_name="National Admin",
             role="ROLE_NATIONAL_ADMIN", county="Nairobi", is_active=True),
        dict(id=str(uuid.uuid4()), username="county1", email="county@test.com",
             hashed_password=hash_password("County1234!"), full_name="County Officer",
             role="ROLE_COUNTY_OFFICER", county="Nairobi", is_active=True),
    ]:
        if not db.query(User).filter(User.username == user_data["username"]).first():
            db.add(User(**user_data))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine_test)


def get_token(username: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.json()}"
    return res.json()["token"]


def test_verify_invalid_serial():
    res = client.get("/api/v1/certificates/verify/INVALID-SERIAL-000")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_full_certificate_flow():
    """End-to-end: create session → approve → add participant + score → approve report → issue certs → verify."""
    trainer_h  = {"Authorization": f"Bearer {get_token('trainer1',  'Trainer1234!')}"}
    county_h   = {"Authorization": f"Bearer {get_token('county1',   'County1234!')}"}
    nat_h      = {"Authorization": f"Bearer {get_token('natadmin',  'NatAdmin1!')}"}

    # 1. Create session
    res = client.post("/api/v1/sessions", json={
        "title": "NASCOP HTS Training", "county": "Nairobi",
        "facility": "KNH", "start_date": "2026-06-01", "end_date": "2026-06-05",
    }, headers=trainer_h)
    assert res.status_code == 201
    sid = res.json()["id"]

    # 2. Approve session
    res = client.patch(f"/api/v1/sessions/{sid}/approve",
                       json={"approved_by": "county1"}, headers=county_h)
    assert res.status_code == 200

    # 3. Add a participant with passing score
    res = client.post(f"/api/v1/sessions/{sid}/participants", json={
        "name": "Jane Wanjiku", "cadre": "Nurse", "facility": "KNH", "status": "PRESENT",
    }, headers=trainer_h)
    assert res.status_code == 201
    pid = res.json()["id"]

    # 4. Record scores (≥80 to be eligible)
    res = client.patch(f"/api/v1/sessions/{sid}/participants/{pid}/scores",
                       json={"pre_test_score": 60, "post_test_score": 85}, headers=trainer_h)
    assert res.status_code == 200

    # 5. Submit report
    res = client.patch(f"/api/v1/sessions/{sid}/report", json={
        "summary": "Training completed successfully.",
        "challenges": "None.", "recommendations": "Continue.",
    }, headers=trainer_h)
    assert res.status_code == 200

    # 6. Approve report
    res = client.patch(f"/api/v1/sessions/{sid}/report/approve", headers=county_h)
    assert res.status_code == 200

    # 7. Issue certificates (national admin)
    res = client.patch(f"/api/v1/certificates/sessions/{sid}/issue", headers=nat_h)
    assert res.status_code == 200
    assert res.json()["certificates_issued"] is True

    # 8. Verify certificate
    serial = res.json()["participants"][0]["certificate_serial"]
    assert serial is not None
    res = client.get(f"/api/v1/certificates/verify/{serial}")
    assert res.status_code == 200
    assert res.json()["valid"] is True
    assert res.json()["participant_name"] == "Jane Wanjiku"