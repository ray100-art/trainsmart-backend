"""MFA, logout revoke, and client-IP audit coverage."""
import pyotp

from app.core.config import settings
from app.core.security import decode_token
from tests.conftest import get_token, auth_headers


def test_logout_revokes_token(client):
    token = get_token(client, "trainer1", "Trainer1234!")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    csrf = client.cookies.get("trainsmart_csrf")
    logout_headers = {**headers}
    if csrf:
        logout_headers["X-CSRF-Token"] = csrf
    assert client.post("/api/v1/auth/logout", headers=logout_headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_mfa_login_flow(client):
    headers = auth_headers(client, "trainer1", "Trainer1234!")
    start = client.post("/api/v1/auth/mfa/setup/start", json={}, headers=headers)
    assert start.status_code == 200, start.json()
    secret = start.json()["secret"]
    code = pyotp.TOTP(secret).now()
    confirm = client.post(
        "/api/v1/auth/mfa/setup/confirm",
        json={"secret": secret, "code": code},
        headers=headers,
    )
    assert confirm.status_code == 200, confirm.json()

    client.cookies.clear()
    login = client.post("/api/v1/auth/login", json={
        "username": "trainer1",
        "password": "Trainer1234!",
    })
    assert login.status_code == 200
    body = login.json()
    assert body["mfa_required"] is True
    assert body["mfa_token"]
    assert not client.cookies.get(settings.COOKIE_NAME)

    bad = client.post("/api/v1/auth/mfa/verify", json={
        "mfa_token": body["mfa_token"],
        "code": "000000",
    })
    assert bad.status_code == 401

    good_code = pyotp.TOTP(secret).now()
    ok = client.post("/api/v1/auth/mfa/verify", json={
        "mfa_token": body["mfa_token"],
        "code": good_code,
    })
    assert ok.status_code == 200, ok.json()
    assert ok.json()["mfa_required"] is False
    assert client.cookies.get(settings.COOKIE_NAME)
    assert client.get("/api/v1/auth/me").status_code == 200


def test_mfa_challenge_token_cannot_call_me(client):
    headers = auth_headers(client, "trainer2", "Trainer5678!")
    start = client.post("/api/v1/auth/mfa/setup/start", json={}, headers=headers)
    secret = start.json()["secret"]
    code = pyotp.TOTP(secret).now()
    client.post(
        "/api/v1/auth/mfa/setup/confirm",
        json={"secret": secret, "code": code},
        headers=headers,
    )
    client.cookies.clear()
    login = client.post("/api/v1/auth/login", json={
        "username": "trainer2",
        "password": "Trainer5678!",
    })
    mfa_token = login.json()["mfa_token"]
    payload = decode_token(mfa_token)
    assert payload["purpose"] == "mfa_challenge"
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {mfa_token}"})
    assert res.status_code == 401


def test_login_audit_records_ip_when_proxy_trusted(client, monkeypatch):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    from tests.conftest import TestingSession
    from app.models.audit_log import AuditLog

    client.post(
        "/api/v1/auth/login",
        json={"username": "county1", "password": "County1234!"},
        headers={"X-Real-IP": "203.0.113.50"},
    )
    db = TestingSession()
    entry = (
        db.query(AuditLog)
        .filter(AuditLog.action == "LOGIN")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    db.close()
    assert entry is not None
    assert entry.ip_address == "203.0.113.50"
