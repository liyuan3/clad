"""End-to-end smoke test against a running uvicorn process and the real frontend
directory. Not part of the pytest suite (it needs a live server); run manually:

    CLAD_DATABASE_URL=sqlite:////tmp/clad-smoke/clad.db .venv/bin/python \
        tests/smoke_live.py http://127.0.0.1:8123

Creates users directly in the same SQLite file the server uses (that is what the
CLI does too). Passwords are random and never printed.
"""

from __future__ import annotations

import secrets
import sys

import httpx
from sqlalchemy import select

from backend.db import Database
from backend.config import Settings
from backend.models import User
from backend.security import hash_password

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8123"
FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"{'PASS' if condition else 'FAIL'} {name}{'' if condition else ' :: ' + detail}")
    if not condition:
        FAILURES.append(name)


def provision(username: str, password: str) -> None:
    settings = Settings.from_env()
    db = Database(settings.database_url)
    db.create_all()
    with db.session() as session:
        if session.scalar(select(User).where(User.username == username)) is None:
            session.add(User(username=username, password_hash=hash_password(password)))
    db.dispose()


def login(client: httpx.Client, username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    alice_pw = secrets.token_urlsafe(18)
    bob_pw = secrets.token_urlsafe(18)
    provision("smoke-alice", alice_pw)
    provision("smoke-bob", bob_pw)

    with httpx.Client(base_url=BASE, timeout=10) as client:
        health = client.get("/api/health")
        check("health 200", health.status_code == 200, health.text)

        index = client.get("/")
        check("GET / serves frontend index", index.status_code == 200 and "CLAD" in index.text)
        asset = client.get("/static/app.js")
        check("GET /static/app.js 200", asset.status_code == 200 and "fetch(" in asset.text)

        check(
            "wrong password 401",
            client.post("/api/auth/login", json={"username": "smoke-alice", "password": "nope"}).status_code == 401,
        )
        check("no token 401", client.get("/api/conversations").status_code == 401)

        alice = login(client, "smoke-alice", alice_pw)
        bob = login(client, "smoke-bob", bob_pw)

        devices = client.get("/api/devices", headers=bearer(alice))
        check("alice has no device initially", devices.json() == [], devices.text)

        pairing = client.post("/api/devices/pairing", headers=bearer(alice)).json()
        check("pairing code issued", bool(pairing.get("code")) and pairing["expires_at"].endswith("Z"))

        paired = client.post("/api/runner/pair", json={"code": pairing["code"], "name": "Smoke-PC"})
        check("pair consumes code", paired.status_code == 200, paired.text)
        device_id = paired.json()["device_id"]
        device_token = paired.json()["device_token"]

        reuse = client.post("/api/runner/pair", json={"code": pairing["code"], "name": "Second"})
        check("code is single use", reuse.status_code == 400, reuse.text)

        self_check = client.get("/api/runner/device", headers=bearer(device_token))
        check(
            "device token authenticates",
            self_check.status_code == 200 and self_check.json()["id"] == device_id,
            self_check.text,
        )
        check(
            "device token rejected on user API",
            client.get("/api/devices", headers=bearer(device_token)).status_code == 401,
        )

        devices = client.get("/api/devices", headers=bearer(alice)).json()
        check(
            "alice sees her device",
            [(d["id"], d["status"]) for d in devices] == [(device_id, "offline")],
            str(devices),
        )
        check("bob sees no devices", client.get("/api/devices", headers=bearer(bob)).json() == [])

        created = client.post(
            "/api/conversations",
            headers=bearer(alice),
            json={"device_id": device_id, "title": "冒烟测试会话"},
        )
        check("conversation created", created.status_code == 200, created.text)
        conversation_id = created.json()["id"]

        check(
            "history starts empty",
            client.get(f"/api/conversations/{conversation_id}/messages", headers=bearer(alice)).json() == [],
        )
        denied = client.get(f"/api/conversations/{conversation_id}/messages", headers=bearer(bob))
        check("bob cannot read alice's conversation", denied.status_code == 404, denied.text)
        denied_device = client.post(
            "/api/conversations", headers=bearer(bob), json={"device_id": device_id, "title": "越权"}
        )
        check("bob cannot create on alice's device", denied_device.status_code == 404, denied_device.text)

        second_pairing = client.post("/api/devices/pairing", headers=bearer(alice)).json()
        second_device = client.post("/api/runner/pair", json={"code": second_pairing["code"], "name": "PC-2"})
        check("second device rejected 409", second_device.status_code == 409, second_device.text)

    print(f"\n{'ALL SMOKE CHECKS PASSED' if not FAILURES else 'FAILURES: ' + ', '.join(FAILURES)}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
