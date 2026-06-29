"""Tests for training programs and audit logs."""
from tests.conftest import get_token


def test_list_and_seed_programs(client):
    admin_h = {"Authorization": f"Bearer {get_token(client, 'sysadmin', 'Admin1234!')}"}
    trainer_h = {"Authorization": f"Bearer {get_token(client, 'trainer1', 'Trainer1234!')}"}

    res = client.post("/api/v1/programs/seed", headers=admin_h)
    assert res.status_code == 201
    assert res.json()["seeded"] >= 1

    res = client.get("/api/v1/programs", headers=trainer_h)
    assert res.status_code == 200
    assert len(res.json()) >= 1
    assert res.json()[0]["code"].startswith("NHITC")


def test_session_with_program(client):
    admin_h = {"Authorization": f"Bearer {get_token(client, 'sysadmin', 'Admin1234!')}"}
    trainer_h = {"Authorization": f"Bearer {get_token(client, 'trainer1', 'Trainer1234!')}"}

    client.post("/api/v1/programs/seed", headers=admin_h)
    programs = client.get("/api/v1/programs", headers=trainer_h).json()
    program_id = programs[0]["id"]

    res = client.post("/api/v1/sessions", json={
        "title": "Nairobi HTS Rollout",
        "program_id": program_id,
        "county": "Nairobi",
        "facility": "KNH",
        "start_date": "2026-07-01",
        "end_date": "2026-07-03",
    }, headers=trainer_h)
    assert res.status_code == 201
    data = res.json()
    assert data["program_id"] == program_id
    assert data["program_code"] == programs[0]["code"]


def test_audit_logs(client):
    me_h = {"Authorization": f"Bearer {get_token(client, 'natadmin', 'NatAdmin1!')}"}
    res = client.get("/api/v1/audit/logs", headers=me_h)
    assert res.status_code == 200
    assert "items" in res.json()
    assert "total" in res.json()
