"""
Session tests.
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

TEST_DB_URL = "sqlite:///./test_sessions.db"

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
    # Seed admin + trainer
    for user_data in [
        dict(id=str(uuid.uuid4()), username="sysadmin", email="admin@test.com",
             hashed_password=hash_password("Admin1234!"), full_name="Admin",
             role="ROLE_SYSTEM_ADMIN", county="Nairobi", is_active=True),
        dict(id=str(uuid.uuid4()), username="trainer1", email="trainer@test.com",
             hashed_password=hash_password("Trainer1234!"), full_name="Trainer One",
             role="ROLE_TRAINER", county="Nairobi", is_active=True),
        dict(id=str(uuid.uuid4()), username="trainer2", email="trainer2@test.com",
             hashed_password=hash_password("Trainer5678!"), full_name="Trainer Two",
             role="ROLE_TRAINER", county="Mombasa", is_active=True),
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


def test_create_and_list_sessions():
    token = get_token("trainer1", "Trainer1234!")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/sessions", json={
        "title":      "NASCOP ART Training",
        "county":     "Nairobi",
        "facility":   "KNH",
        "start_date": "2026-06-01",
        "end_date":   "2026-06-05",
        "status":     "UPCOMING",
    }, headers=headers)
    assert res.status_code == 201, res.json()
    session_id = res.json()["id"]

    res = client.get("/api/v1/sessions", headers=headers)
    assert res.status_code == 200
    assert session_id in [s["id"] for s in res.json()]


def test_update_session_title_does_not_reset_approval():
    """Editing only the title should NOT reset approval_status to PENDING."""
    token = get_token("trainer1", "Trainer1234!")
    headers = {"Authorization": f"Bearer {token}"}

    # Create session
    res = client.post("/api/v1/sessions", json={
        "title": "Old Title", "county": "Nairobi", "facility": "KNH",
        "start_date": "2026-07-01", "end_date": "2026-07-03",
    }, headers=headers)
    session_id = res.json()["id"]

    # Manually approve via admin
    admin_token = get_token("sysadmin", "Admin1234!")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    client.patch(f"/api/v1/sessions/{session_id}/approve",
                 json={"approved_by": "sysadmin"}, headers=admin_headers)

    # Edit only the title
    res = client.patch(f"/api/v1/sessions/{session_id}",
                       json={"title": "New Title"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["approval_status"] == "APPROVED"  # must stay APPROVED


def test_update_session_county_resets_approval():
    """Editing county (material field) SHOULD reset approval_status to PENDING."""
    token = get_token("trainer1", "Trainer1234!")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/sessions", json={
        "title": "Test Session", "county": "Nairobi", "facility": "KNH",
        "start_date": "2026-08-01", "end_date": "2026-08-03",
    }, headers=headers)
    session_id = res.json()["id"]

    admin_token = get_token("sysadmin", "Admin1234!")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    client.patch(f"/api/v1/sessions/{session_id}/approve",
                 json={"approved_by": "sysadmin"}, headers=admin_headers)

    res = client.patch(f"/api/v1/sessions/{session_id}",
                       json={"county": "Mombasa"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["approval_status"] == "PENDING"  # must reset


def test_delete_session():
    token = get_token("trainer1", "Trainer1234!")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/sessions", json={
        "title": "To Delete", "county": "Kisumu", "facility": "JOOTRH",
        "start_date": "2026-09-01", "end_date": "2026-09-02",
    }, headers=headers)
    session_id = res.json()["id"]

    res = client.delete(f"/api/v1/sessions/{session_id}", headers=headers)
    assert res.status_code == 204

    res = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert res.status_code == 404


def test_session_ownership_enforcement():
    # 1. trainer1 creates a session
    token1 = get_token("trainer1", "Trainer1234!")
    headers1 = {"Authorization": f"Bearer {token1}"}

    res = client.post("/api/v1/sessions", json={
        "title": "Trainer 1 Session", "county": "Nairobi", "facility": "KNH",
        "start_date": "2026-06-01", "end_date": "2026-06-05",
    }, headers=headers1)
    assert res.status_code == 201
    sid = res.json()["id"]

    # 2. trainer2 tries to edit trainer1's session (should fail)
    token2 = get_token("trainer2", "Trainer5678!")
    headers2 = {"Authorization": f"Bearer {token2}"}

    res = client.patch(f"/api/v1/sessions/{sid}", json={"title": "Hack title"}, headers=headers2)
    assert res.status_code == 403
    assert "do not own" in res.json()["detail"]

    # 3. trainer2 tries to delete trainer1's session (should fail)
    res = client.delete(f"/api/v1/sessions/{sid}", headers=headers2)
    assert res.status_code == 403

    # 4. admin tries to edit trainer1's session (should succeed)
    admin_token = get_token("sysadmin", "Admin1234!")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    res = client.patch(f"/api/v1/sessions/{sid}", json={"title": "Admin Edit"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["title"] == "Admin Edit"


def test_session_date_validations():
    token = get_token("trainer1", "Trainer1234!")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Invalid date format on create (should fail with 422)
    res = client.post("/api/v1/sessions", json={
        "title": "Bad Date Format", "county": "Nairobi", "facility": "KNH",
        "start_date": "06/01/2026", "end_date": "2026-06-05",
    }, headers=headers)
    assert res.status_code == 422

    # 2. start_date > end_date on create (should fail with 422)
    res = client.post("/api/v1/sessions", json={
        "title": "Bad Date Range", "county": "Nairobi", "facility": "KNH",
        "start_date": "2026-06-05", "end_date": "2026-06-01",
    }, headers=headers)
    assert res.status_code == 422

    # 3. Create valid session first
    res = client.post("/api/v1/sessions", json={
        "title": "Valid Dates", "county": "Nairobi", "facility": "KNH",
        "start_date": "2026-06-01", "end_date": "2026-06-05",
    }, headers=headers)
    assert res.status_code == 201
    sid = res.json()["id"]

    # 4. Update with invalid range (start_date > end_date) (should fail with 400)
    res = client.patch(f"/api/v1/sessions/{sid}", json={"start_date": "2026-06-07"}, headers=headers)
    assert res.status_code == 400
    assert "start_date must be before" in res.json()["detail"]