"""Tests for legacy certificate verification and import."""
import io

from tests.conftest import get_token


def test_verify_legacy_certificate(client):
    admin_h = {"Authorization": f"Bearer {get_token(client, 'sysadmin', 'Admin1234!')}"}

    csv_data = """serial,participant_name,cadre,facility,course,county,start_date,end_date,post_test_score,issued_date,era
LEG-PRE-2015-001,Peter Ochieng,Nurse,KNH,HIV Basics,Nairobi,2015-03-01,2015-03-05,90,2015-03-10,pre_2018
"""
    res = client.post(
        "/api/v1/certificates/legacy/import",
        files={"file": ("legacy.csv", io.BytesIO(csv_data.encode()), "text/csv")},
        headers=admin_h,
    )
    assert res.status_code == 200
    assert res.json()["imported"] == 1

    res = client.get("/api/v1/certificates/verify/LEG-PRE-2015-001?era=pre_2018")
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["source"] == "legacy"
    assert data["era"] == "pre_2018"
    assert data["participant_name"] == "Peter Ochieng"


def test_verify_legacy_wrong_era_not_found(client):
    admin_h = {"Authorization": f"Bearer {get_token(client, 'sysadmin', 'Admin1234!')}"}
    csv_data = """serial,participant_name,cadre,facility,course,county,start_date,end_date,post_test_score,issued_date,era
LEG-POST-2019-001,Mary Achieng,Nurse,KNH,HIV Refresher,Nairobi,2019-03-01,2019-03-05,88,2019-03-10,post_2018
"""
    client.post(
        "/api/v1/certificates/legacy/import",
        files={"file": ("legacy.csv", io.BytesIO(csv_data.encode()), "text/csv")},
        headers=admin_h,
    )

    res = client.get("/api/v1/certificates/verify/LEG-POST-2019-001?era=pre_2018")
    assert res.status_code == 404


def test_bulk_import_participants(client):
    trainer_h = {"Authorization": f"Bearer {get_token(client, 'trainer1', 'Trainer1234!')}"}
    county_h = {"Authorization": f"Bearer {get_token(client, 'county1', 'County1234!')}"}

    res = client.post("/api/v1/sessions", json={
        "title": "Bulk Import Training", "county": "Nairobi",
        "facility": "KNH", "start_date": "2026-06-01", "end_date": "2026-06-05",
    }, headers=trainer_h)
    sid = res.json()["id"]
    client.patch(f"/api/v1/sessions/{sid}/approve", headers=county_h)

    csv_data = """name,cadre,facility,staff_number,status,pre_test_score,post_test_score
Alice Mwangi,Nurse,KNH,MOH001,PRESENT,60,85
Bob Otieno,Doctor,KNH,,PRESENT,70,90
"""
    res = client.post(
        f"/api/v1/sessions/{sid}/participants/import",
        files={"file": ("participants.csv", io.BytesIO(csv_data.encode()), "text/csv")},
        headers=trainer_h,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["imported"] == 2
    assert body["errors"] == []

    res = client.get(f"/api/v1/sessions/{sid}", headers=trainer_h)
    assert len(res.json()["participants"]) == 2
