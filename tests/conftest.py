from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings
from backend.models import AuthSession, PairingCode, User, utcnow
from backend.security import hash_password, new_token, normalize_pairing_code, token_hash

PASSWORD = "correct-horse-9"


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        frontend_dir=tmp_path / "frontend",
        session_ttl_seconds=3600,
        pairing_ttl_seconds=600,
    )


@pytest.fixture
def app(settings):
    return create_app(settings=settings)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(app):
    def _make(username: str, password: str = PASSWORD) -> str:
        with app.state.db.session() as session:
            user = User(username=username, password_hash=hash_password(password))
            session.add(user)
            session.flush()
            return user.id

    return _make


@pytest.fixture
def login(client):
    def _login(username: str, password: str = PASSWORD) -> str:
        response = client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    return _login


@pytest.fixture
def make_device(client, make_user, login):
    """Provision a user, issue a pairing code and consume it. Returns a dict with
    user_id / device_id / device_token / headers."""

    def _make(username: str, device_name: str = "测试设备") -> dict:
        user_id = make_user(username)
        token = login(username)
        headers = {"Authorization": f"Bearer {token}"}
        code = client.post("/api/devices/pairing", headers=headers).json()["code"]
        paired = client.post("/api/runner/pair", json={"code": code, "name": device_name})
        assert paired.status_code == 200, paired.text
        body = paired.json()
        return {
            "user_id": user_id,
            "user_token": token,
            "headers": headers,
            "device_id": body["device_id"],
            "device_token": body["device_token"],
        }

    return _make


@pytest.fixture
def expire_pairing_code(app):
    def _expire(code: str) -> None:
        normalized = normalize_pairing_code(code)
        assert normalized
        with app.state.db.session() as session:
            record = (
                session.query(PairingCode)
                .filter(PairingCode.code_hash == token_hash(normalized))
                .one()
            )
            record.expires_at = utcnow() - timedelta(seconds=1)

    return _expire


@pytest.fixture
def expire_session(app):
    def _expire(raw_token: str) -> None:
        with app.state.db.session() as session:
            record = (
                session.query(AuthSession)
                .filter(AuthSession.token_hash == token_hash(raw_token))
                .one()
            )
            record.expires_at = utcnow() - timedelta(seconds=1)

    return _expire


@pytest.fixture
def raw_session_token():
    """A token value we can insert directly to test expiry."""
    return new_token()
