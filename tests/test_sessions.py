"""Session tests."""
from tests.conftest import get_token


def test_create_and_list_sessions(client):
    token = get_token(client, "trainer1", "Trainer1234!")
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


def test_update_session_title_does_not_reset_approval(client):
    token = get_token(client, "trainer1", "Trainer1234!")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/sessions", json={
        "title": "Old Title", "county": "Nairobi", "facility": "KNH",
        "start_date": "2026-07-01", "end_date": "2026-07-03",
    }, headers=headers)
    session_id = res.json()["id"]

    admin_headers = {"Authorization": f"Bearer {get_token(client, 'sysadmin', 'Admin1234!')}"}
    client.patch(f"/api/v1/sessions/{session_id}/approve", headers=admin_headers)

    res = client.patch(f"/api/v1/sessions/{session_id}",
                       json={"title": "New Title"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["approval_status"] == "APPROVED"


def test_update_session_county_resets_approval(client):
    token = get_token(client, "trainer1", "Trainer1234!")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/sessions", json={
        "title": "Test Session", "county": "Nairobi", "facility": "KNH",
        "start_date": "2026-08-01", "end_date": "2026-08-03",
    }, headers=headers)
    session_id = res.json()["id"]

    admin_headers = {"Authorization": f"Bearer {get_token(client, 'sysadmin', 'Admin1234!')}"}
    client.patch(f"/api/v1/sessions/{session_id}/approve", headers=admin_headers)

    res = client.patch(f"/api/v1/sessions/{session_id}",
                       json={"county": "Mombasa"}, headers=headers)
    assert res.status_code == 403


def test_trainer_cannot_create_session_in_other_county(client):
    headers = {"Authorization": f"Bearer {get_token(client, 'trainer1', 'Trainer1234!')}"}
    res = client.post("/api/v1/sessions", json={
        "title": "Wrong County", "county": "Kisumu", "facility": "JOOTRH",
        "start_date": "2026-09-01", "end_date": "2026-09-02",
    }, headers=headers)
    assert res.status_code == 403


def test_delete_session(client):
    token = get_token(client, "trainer1", "Trainer1234!")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/sessions", json={
        "title": "To Delete", "county": "Nairobi", "facility": "JOOTRH",
        "start_date": "2026-09-01", "end_date": "2026-09-02",
    }, headers=headers)
    session_id = res.json()["id"]

    res = client.delete(f"/api/v1/sessions/{session_id}", headers=headers)
    assert res.status_code == 204

    res = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert res.status_code == 404


def test_session_ownership_enforcement(client):
    headers1 = {"Authorization": f"Bearer {get_token(client, 'trainer1', 'Trainer1234!')}"}

    res = client.post("/api/v1/sessions", json={
        "title": "Trainer 1 Session", "county": "Nairobi", "facility": "KNH",
        "start_date": "2026-06-01", "end_date": "2026-06-05",
    }, headers=headers1)
    sid = res.json()["id"]

    headers2 = {"Authorization": f"Bearer {get_token(client, 'trainer2', 'Trainer5678!')}"}
    res = client.patch(f"/api/v1/sessions/{sid}", json={"title": "Hack title"}, headers=headers2)
    assert res.status_code == 403

    res = client.get(f"/api/v1/sessions/{sid}", headers=headers2)
    assert res.status_code == 403

    res = client.delete(f"/api/v1/sessions/{sid}", headers=headers2)
    assert res.status_code == 403

    admin_headers = {"Authorization": f"Bearer {get_token(client, 'sysadmin', 'Admin1234!')}"}
    res = client.patch(f"/api/v1/sessions/{sid}", json={"title": "Admin Edit"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["title"] == "Admin Edit"


def test_session_date_validations(client):
    headers = {"Authorization": f"Bearer {get_token(client, 'trainer1', 'Trainer1234!')}"}

    res = client.post("/api/v1/sessions", json={
        "title": "Bad Date Format", "county": "Nairobi", "facility": "KNH",
        "start_date": "06/01/2026", "end_date": "2026-06-05",
    }, headers=headers)
    assert res.status_code == 422

    res = client.post("/api/v1/sessions", json={
        "title": "Bad Date Range", "county": "Nairobi", "facility": "KNH",
        "start_date": "2026-06-05", "end_date": "2026-06-01",
    }, headers=headers)
    assert res.status_code == 422

    res = client.post("/api/v1/sessions", json={
        "title": "Valid Dates", "county": "Nairobi", "facility": "KNH",
        "start_date": "2026-06-01", "end_date": "2026-06-05",
    }, headers=headers)
    sid = res.json()["id"]

    res = client.patch(f"/api/v1/sessions/{sid}", json={"start_date": "2026-06-07"}, headers=headers)
    assert res.status_code == 400
    assert "start_date must be before" in res.json()["detail"]


def test_county_officer_cannot_approve_other_county(client):
    trainer_h = {"Authorization": f"Bearer {get_token(client, 'trainer2', 'Trainer5678!')}"}
    res = client.post("/api/v1/sessions", json={
        "title": "Mombasa Training", "county": "Mombasa", "facility": "Coast GH",
        "start_date": "2026-06-01", "end_date": "2026-06-05",
    }, headers=trainer_h)
    sid = res.json()["id"]

    nairobi_county_h = {"Authorization": f"Bearer {get_token(client, 'county1', 'County1234!')}"}
    res = client.patch(f"/api/v1/sessions/{sid}/approve", headers=nairobi_county_h)
    assert res.status_code == 403

    nat_h = {"Authorization": f"Bearer {get_token(client, 'natadmin', 'NatAdmin1!')}"}
    res = client.patch(f"/api/v1/sessions/{sid}/approve", headers=nat_h)
    assert res.status_code == 200


def test_participants_blocked_before_approval(client):
    trainer_h = {"Authorization": f"Bearer {get_token(client, 'trainer1', 'Trainer1234!')}"}
    res = client.post("/api/v1/sessions", json={
        "title": "Pending Session", "county": "Nairobi", "facility": "KNH",
        "start_date": "2026-06-01", "end_date": "2026-06-05",
    }, headers=trainer_h)
    sid = res.json()["id"]

    res = client.post(f"/api/v1/sessions/{sid}/participants", json={
        "name": "Jane Doe", "cadre": "Nurse", "facility": "KNH",
    }, headers=trainer_h)
    assert res.status_code == 400
    assert "approved" in res.json()["detail"].lower()


def test_cannot_delete_session_after_certificates(client):
    trainer_h = {"Authorization": f"Bearer {get_token(client, 'trainer1', 'Trainer1234!')}"}
    county_h = {"Authorization": f"Bearer {get_token(client, 'county1', 'County1234!')}"}
    nat_h = {"Authorization": f"Bearer {get_token(client, 'natadmin', 'NatAdmin1!')}"}

    res = client.post("/api/v1/sessions", json={
        "title": "Cert Session", "county": "Nairobi", "facility": "KNH",
        "start_date": "2026-06-01", "end_date": "2026-06-05",
    }, headers=trainer_h)
    sid = res.json()["id"]

    client.patch(f"/api/v1/sessions/{sid}/approve", headers=county_h)
    res = client.post(f"/api/v1/sessions/{sid}/participants", json={
        "name": "John Doe", "cadre": "Nurse", "facility": "KNH",
    }, headers=trainer_h)
    pid = res.json()["id"]
    client.patch(f"/api/v1/sessions/{sid}/participants/{pid}/scores",
                 json={"pre_test_score": 70, "post_test_score": 90}, headers=trainer_h)
    client.patch(f"/api/v1/sessions/{sid}/report", json={
        "summary": "Done", "challenges": "", "recommendations": "",
    }, headers=trainer_h)
    client.patch(f"/api/v1/sessions/{sid}/report/approve", headers=county_h)
    client.patch(f"/api/v1/certificates/sessions/{sid}/issue", headers=nat_h)

    res = client.delete(f"/api/v1/sessions/{sid}", headers=trainer_h)
    assert res.status_code == 400
    assert "certificates" in res.json()["detail"].lower()
