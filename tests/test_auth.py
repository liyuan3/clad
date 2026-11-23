"""Login, token lifecycle and "no open registration" behaviour."""

from __future__ import annotations

from sqlalchemy import select

from backend.config import Settings
from backend.models import User
from backend.security import hash_password

from .conftest import PASSWORD


def test_login_returns_token_and_username(client, make_user):
    make_user("alice")
    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["username"] == "alice"
    assert isinstance(body["access_token"], str) and len(body["access_token"]) >= 32


def test_token_grants_access(client, make_user, login):
    make_user("alice")
    token = login("alice")
    response = client.get("/api/devices", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []


def test_wrong_password_rejected(client, make_user):
    make_user("alice")
    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": "wrong-password"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "用户名或密码错误"


def test_unknown_user_gives_same_message_as_wrong_password(client, make_user):
    make_user("alice")
    unknown = client.post(
        "/api/auth/login", json={"username": "nobody", "password": PASSWORD}
    )
    wrong = client.post(
        "/api/auth/login", json={"username": "alice", "password": "wrong-password"}
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_protected_endpoints_require_token(client):
    for path in ("/api/devices", "/api/conversations"):
        response = client.get(path)
        assert response.status_code == 401, path
        assert response.headers.get("www-authenticate") == "Bearer"


def test_invalid_token_rejected(client):
    response = client.get("/api/devices", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_expired_session_rejected(client, make_user, login, expire_session):
    make_user("alice")
    token = login("alice")
    expire_session(token)
    response = client.get("/api/devices", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "过期" in response.json()["detail"]


def test_session_token_is_not_stored_raw(app, client, make_user, login):
    make_user("alice")
    token = login("alice")
    with app.state.db.session() as session:
        stored = session.execute(select(User).where(User.username == "alice")).all()
        assert len(stored) == 1
        from backend.models import AuthSession

        row = session.scalars(select(AuthSession)).all()
        assert len(row) == 1
        assert row[0].token_hash != token


def test_no_registration_endpoint(client):
    response = client.post(
        "/api/auth/register", json={"username": "eve", "password": PASSWORD}
    )
    assert response.status_code == 404


def test_password_never_stored_in_plaintext(app, make_user):
    make_user("bob")
    with app.state.db.session() as session:
        user = session.scalar(select(User).where(User.username == "bob"))
        assert user is not None
        assert PASSWORD not in user.password_hash
        assert user.password_hash.startswith("scrypt$")


def test_password_hash_roundtrip():
    stored = hash_password("correct-horse-9")
    from backend.security import verify_password

    assert verify_password(stored, "correct-horse-9")
    assert not verify_password(stored, "correct-horse-8")
    assert not verify_password("garbage", "correct-horse-9")


def test_settings_reject_bad_ttl(monkeypatch):
    monkeypatch.setenv("CLAD_SESSION_TTL_SECONDS", "not-a-number")
    import pytest

    with pytest.raises(RuntimeError):
        Settings.from_env()
