"""Pairing codes: TTL, single use, one-device-per-user, ownership."""

from __future__ import annotations

import re

from backend.models import Device
from backend.security import token_hash


def test_pairing_code_shape(client, make_user, login):
    make_user("alice")
    token = login("alice")
    response = client.post(
        "/api/devices/pairing", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert re.fullmatch(r"[A-Z0-9]{4}-[A-Z0-9]{4}", body["code"])
    assert body["expires_at"].endswith("Z")


def test_pairing_requires_login(client):
    assert client.post("/api/devices/pairing").status_code == 401


def test_pairing_binds_device_to_code_owner(client, make_user, login):
    make_user("alice")
    make_user("bob")
    alice = login("alice")
    bob = login("bob")

    code = client.post(
        "/api/devices/pairing", headers={"Authorization": f"Bearer {alice}"}
    ).json()["code"]
    paired = client.post("/api/runner/pair", json={"code": code, "name": "Alice-PC"})
    assert paired.status_code == 200, paired.text
    device_id = paired.json()["device_id"]
    assert paired.json()["device_token"]

    alice_devices = client.get(
        "/api/devices", headers={"Authorization": f"Bearer {alice}"}
    ).json()
    bob_devices = client.get(
        "/api/devices", headers={"Authorization": f"Bearer {bob}"}
    ).json()
    assert [(d["id"], d["name"], d["status"]) for d in alice_devices] == [
        (device_id, "Alice-PC", "offline")
    ]
    assert bob_devices == []


def test_pairing_code_single_use(client, make_user, login):
    make_user("alice")
    token = login("alice")
    code = client.post(
        "/api/devices/pairing", headers={"Authorization": f"Bearer {token}"}
    ).json()["code"]

    first = client.post("/api/runner/pair", json={"code": code, "name": "PC-1"})
    assert first.status_code == 200
    second = client.post("/api/runner/pair", json={"code": code, "name": "PC-2"})
    assert second.status_code == 400
    assert second.json()["detail"] == "配对码无效或已过期"


def test_pairing_code_expires(client, make_user, login, expire_pairing_code):
    make_user("alice")
    token = login("alice")
    code = client.post(
        "/api/devices/pairing", headers={"Authorization": f"Bearer {token}"}
    ).json()["code"]
    expire_pairing_code(code)

    response = client.post("/api/runner/pair", json={"code": code, "name": "PC-1"})
    assert response.status_code == 400
    assert client.get(
        "/api/devices", headers={"Authorization": f"Bearer {token}"}
    ).json() == []


def test_new_code_invalidates_previous(client, make_user, login):
    make_user("alice")
    token = login("alice")
    headers = {"Authorization": f"Bearer {token}"}
    old_code = client.post("/api/devices/pairing", headers=headers).json()["code"]
    new_code = client.post("/api/devices/pairing", headers=headers).json()["code"]

    assert client.post("/api/runner/pair", json={"code": old_code, "name": "PC"}).status_code == 400
    assert client.post("/api/runner/pair", json={"code": new_code, "name": "PC"}).status_code == 200


def test_second_device_rejected(client, make_user, login):
    make_user("alice")
    token = login("alice")
    headers = {"Authorization": f"Bearer {token}"}
    first_code = client.post("/api/devices/pairing", headers=headers).json()["code"]
    assert client.post("/api/runner/pair", json={"code": first_code, "name": "PC-1"}).status_code == 200

    second_code = client.post("/api/devices/pairing", headers=headers).json()["code"]
    response = client.post("/api/runner/pair", json={"code": second_code, "name": "PC-2"})
    assert response.status_code == 409
    assert len(client.get("/api/devices", headers=headers).json()) == 1


def test_unknown_code_rejected(client):
    response = client.post("/api/runner/pair", json={"code": "ZZZZ-ZZZZ", "name": "PC"})
    assert response.status_code == 400


def test_code_is_normalised_for_typing(client, make_user, login):
    make_user("alice")
    token = login("alice")
    code = client.post(
        "/api/devices/pairing", headers={"Authorization": f"Bearer {token}"}
    ).json()["code"]
    sloppy = code.lower().replace("-", " ")
    assert client.post("/api/runner/pair", json={"code": sloppy, "name": "PC"}).status_code == 200


def test_device_token_authenticates_as_device(client, app, make_device):
    device = make_device("alice")
    response = client.get(
        "/api/runner/device",
        headers={"Authorization": f"Bearer {device['device_token']}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["id"] == device["device_id"]

    with app.state.db.session() as session:
        stored = session.get(Device, device["device_id"])
        assert stored is not None
        assert stored.token_hash == token_hash(device["device_token"])
        assert stored.token_hash != device["device_token"]


def test_device_token_cannot_use_user_api(client, make_device):
    device = make_device("alice")
    response = client.get(
        "/api/devices", headers={"Authorization": f"Bearer {device['device_token']}"}
    )
    assert response.status_code == 401


def test_user_token_cannot_use_device_api(client, make_user, login):
    make_user("alice")
    token = login("alice")
    response = client.get(
        "/api/runner/device", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
