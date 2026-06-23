"""Auth tests."""
from tests.conftest import get_token


def test_register_and_login(client):
    token = get_token(client, "sysadmin", "Admin1234!")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/auth/register", json={
        "username":  "testtrainer",
        "email":     "newtrainer@test.com",
        "password":  "Trainer1234!",
        "full_name": "Test Trainer",
        "role":      "ROLE_TRAINER",
        "county":    "Nairobi",
    }, headers=headers)
    assert res.status_code == 201, res.json()

    res = client.post("/api/v1/auth/login", json={
        "username": "testtrainer",
        "password": "Trainer1234!",
    })
    assert res.status_code == 200
    assert res.json()["role"] == "ROLE_TRAINER"


def test_login_wrong_password(client):
    res = client.post("/api/v1/auth/login", json={
        "username": "sysadmin",
        "password": "wrongpassword",
    })
    assert res.status_code == 401


def test_login_nonexistent_user(client):
    res = client.post("/api/v1/auth/login", json={
        "username": "nobody",
        "password": "Whatever1!",
    })
    assert res.status_code == 401


def test_weak_password_rejected(client):
    headers = {"Authorization": f"Bearer {get_token(client, 'sysadmin', 'Admin1234!')}"}
    res = client.post("/api/v1/auth/register", json={
        "username":  "weakuser",
        "email":     "weak@test.com",
        "password":  "test1234",
        "full_name": "Weak User",
        "role":      "ROLE_TRAINER",
        "county":    "Nairobi",
    }, headers=headers)
    assert res.status_code == 400
    assert "Password must contain" in res.json()["detail"]


def test_duplicate_username_rejected(client):
    headers = {"Authorization": f"Bearer {get_token(client, 'sysadmin', 'Admin1234!')}"}
    payload = {
        "username":  "dupuser",
        "email":     "dup@test.com",
        "password":  "Secure1234!",
        "full_name": "Dup User",
        "role":      "ROLE_TRAINER",
        "county":    "Nairobi",
    }
    assert client.post("/api/v1/auth/register", json=payload, headers=headers).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload, headers=headers).status_code == 409
