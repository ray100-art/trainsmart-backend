"""Logout revoke and client-IP audit coverage (MFA temporarily disabled)."""
from app.core.config import settings
from tests.conftest import get_token


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


def test_mfa_endpoints_disabled(client):
    res = client.post("/api/v1/auth/mfa/verify", json={
        "mfa_token": "not-a-real-token",
        "code": "123456",
    })
    assert res.status_code == 503
    assert "disabled" in res.json()["detail"].lower()


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


def test_password_login_ignores_enrolled_mfa_when_disabled(client):
    """Even if a user previously enrolled MFA, login must issue a cookie while MFA_ENABLED=False."""
    from tests.conftest import TestingSession
    from app.models.user import User

    db = TestingSession()
    user = db.query(User).filter(User.username == "trainer1").first()
    assert user is not None
    user.mfa_enabled = True
    user.mfa_secret = "JBSWY3DPEHPK3PXP"
    db.commit()
    db.close()

    client.cookies.clear()
    res = client.post("/api/v1/auth/login", json={
        "username": "trainer1",
        "password": "Trainer1234!",
    })
    assert res.status_code == 200
    body = res.json()
    assert body.get("mfa_required") is False
    assert client.cookies.get(settings.COOKIE_NAME)
