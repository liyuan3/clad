"""Device listing and per-user isolation."""

from __future__ import annotations


def test_new_user_has_no_devices(client, make_user, login):
    make_user("alice")
    token = login("alice")
    assert client.get("/api/devices", headers={"Authorization": f"Bearer {token}"}).json() == []


def test_devices_are_scoped_per_user(client, make_device, make_user, login):
    make_device("alice", device_name="Alice-PC")
    make_user("bob")
    bob_token = login("bob")

    response = client.get("/api/devices", headers={"Authorization": f"Bearer {bob_token}"})
    assert response.status_code == 200
    assert response.json() == []


def test_device_status_is_from_allowed_set(client, make_device):
    device = make_device("alice")
    listed = client.get(
        "/api/devices", headers={"Authorization": f"Bearer {device['user_token']}"}
    ).json()
    assert len(listed) == 1
    assert listed[0]["status"] in {"online", "offline", "busy"}
    assert listed[0]["status"] == "offline"  # no runner connected yet
    assert set(listed[0]) == {"id", "name", "status"}
