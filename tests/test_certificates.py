"""Certificate tests."""
from tests.conftest import get_token


def test_verify_invalid_serial(client):
    res = client.get("/api/v1/certificates/verify/INVALID-SERIAL-000")
    assert res.status_code == 404


def test_full_certificate_flow(client):
    trainer_h = {"Authorization": f"Bearer {get_token(client, 'trainer1', 'Trainer1234!')}"}
    county_h  = {"Authorization": f"Bearer {get_token(client, 'county1', 'County1234!')}"}
    nat_h     = {"Authorization": f"Bearer {get_token(client, 'natadmin', 'NatAdmin1!')}"}

    res = client.post("/api/v1/sessions", json={
        "title": "NASCOP HTS Training", "county": "Nairobi",
        "facility": "KNH", "start_date": "2026-06-01", "end_date": "2026-06-05",
    }, headers=trainer_h)
    sid = res.json()["id"]

    res = client.patch(f"/api/v1/sessions/{sid}/approve", headers=county_h)
    assert res.status_code == 200
    assert res.json()["approved_by_name"] == "County Officer"

    res = client.post(f"/api/v1/sessions/{sid}/participants", json={
        "name": "Jane Wanjiku", "cadre": "Nurse", "facility": "KNH", "status": "PRESENT",
    }, headers=trainer_h)
    pid = res.json()["id"]

    res = client.patch(f"/api/v1/sessions/{sid}/participants/{pid}/scores",
                       json={"pre_test_score": 60, "post_test_score": 85}, headers=trainer_h)
    assert res.status_code == 200

    res = client.patch(f"/api/v1/sessions/{sid}/report", json={
        "summary": "Training completed successfully.",
        "challenges": "None.", "recommendations": "Continue.",
    }, headers=trainer_h)
    assert res.status_code == 200

    res = client.patch(f"/api/v1/sessions/{sid}/report/approve", headers=county_h)
    assert res.status_code == 200

    res = client.patch(f"/api/v1/certificates/sessions/{sid}/issue", headers=nat_h)
    assert res.status_code == 200
    assert res.json()["certificates_issued"] is True

    serial = res.json()["participants"][0]["certificate_serial"]
    res = client.get(f"/api/v1/certificates/verify/{serial}")
    assert res.status_code == 200
    assert res.json()["valid"] is True
    assert res.json()["participant_name"] == "Jane Wanjiku"


def test_invalid_score_rejected(client):
    trainer_h = {"Authorization": f"Bearer {get_token(client, 'trainer1', 'Trainer1234!')}"}
    county_h = {"Authorization": f"Bearer {get_token(client, 'county1', 'County1234!')}"}

    res = client.post("/api/v1/sessions", json={
        "title": "Score Test", "county": "Nairobi", "facility": "KNH",
        "start_date": "2026-06-01", "end_date": "2026-06-05",
    }, headers=trainer_h)
    sid = res.json()["id"]
    client.patch(f"/api/v1/sessions/{sid}/approve", headers=county_h)

    res = client.post(f"/api/v1/sessions/{sid}/participants", json={
        "name": "Test User", "cadre": "Nurse", "facility": "KNH",
    }, headers=trainer_h)
    pid = res.json()["id"]

    res = client.patch(f"/api/v1/sessions/{sid}/participants/{pid}/scores",
                       json={"pre_test_score": 150, "post_test_score": 85}, headers=trainer_h)
    assert res.status_code == 422
