"""Conversations and message history, including cross-user denial."""

from __future__ import annotations

from datetime import timedelta

from backend.models import Conversation, Message, utcnow


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_conversation(client, make_device):
    device = make_device("alice")
    created = client.post(
        "/api/conversations",
        headers=device["headers"],
        json={"device_id": device["device_id"], "title": "写一个周报"},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["title"] == "写一个周报"
    assert body["device_id"] == device["device_id"]
    assert body["created_at"].endswith("Z")

    listed = client.get("/api/conversations", headers=device["headers"]).json()
    assert [c["id"] for c in listed] == [body["id"]]


def test_conversations_are_newest_first(client, make_device):
    device = make_device("alice")
    ids = []
    for title in ("第一条", "第二条", "第三条"):
        ids.append(
            client.post(
                "/api/conversations",
                headers=device["headers"],
                json={"device_id": device["device_id"], "title": title},
            ).json()["id"]
        )
    listed = client.get("/api/conversations", headers=device["headers"]).json()
    assert [c["id"] for c in listed] == list(reversed(ids))


def test_conversation_list_is_scoped_per_user(client, make_device, make_user, login):
    alice = make_device("alice")
    client.post(
        "/api/conversations",
        headers=alice["headers"],
        json={"device_id": alice["device_id"], "title": "Alice 的会话"},
    )
    make_user("bob")
    bob_headers = _auth(login("bob"))
    assert client.get("/api/conversations", headers=bob_headers).json() == []


def test_cannot_create_conversation_on_other_users_device(client, make_device, make_user, login):
    alice = make_device("alice")
    make_user("bob")
    bob_headers = _auth(login("bob"))

    response = client.post(
        "/api/conversations",
        headers=bob_headers,
        json={"device_id": alice["device_id"], "title": "越权"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "设备不存在"


def test_cannot_create_conversation_on_unknown_device(client, make_device):
    device = make_device("alice")
    response = client.post(
        "/api/conversations",
        headers=device["headers"],
        json={"device_id": "does-not-exist", "title": "x"},
    )
    assert response.status_code == 404


def test_blank_title_rejected(client, make_device):
    device = make_device("alice")
    response = client.post(
        "/api/conversations",
        headers=device["headers"],
        json={"device_id": device["device_id"], "title": "   "},
    )
    assert response.status_code == 422


def test_messages_empty_for_new_conversation(client, make_device):
    device = make_device("alice")
    conversation = client.post(
        "/api/conversations",
        headers=device["headers"],
        json={"device_id": device["device_id"], "title": "空会话"},
    ).json()
    messages = client.get(
        f"/api/conversations/{conversation['id']}/messages", headers=device["headers"]
    )
    assert messages.status_code == 200
    assert messages.json() == []


def test_messages_are_ordered_and_typed(app, client, make_device):
    device = make_device("alice")
    conversation = client.post(
        "/api/conversations",
        headers=device["headers"],
        json={"device_id": device["device_id"], "title": "历史"},
    ).json()

    base = utcnow()
    with app.state.db.session() as session:
        session.add_all(
            [
                Message(
                    conversation_id=conversation["id"],
                    role="user",
                    content="第一问",
                    created_at=base,
                ),
                Message(
                    conversation_id=conversation["id"],
                    role="assistant",
                    content="第一答",
                    created_at=base + timedelta(seconds=1),
                ),
            ]
        )

    messages = client.get(
        f"/api/conversations/{conversation['id']}/messages", headers=device["headers"]
    ).json()
    assert [(m["role"], m["content"]) for m in messages] == [
        ("user", "第一问"),
        ("assistant", "第一答"),
    ]
    assert all(m["created_at"].endswith("Z") for m in messages)


def test_cannot_read_other_users_messages(app, client, make_device, make_user, login):
    alice = make_device("alice")
    conversation = client.post(
        "/api/conversations",
        headers=alice["headers"],
        json={"device_id": alice["device_id"], "title": "私密"},
    ).json()
    with app.state.db.session() as session:
        session.add(
            Message(conversation_id=conversation["id"], role="user", content="机密内容")
        )

    make_user("bob")
    bob_headers = _auth(login("bob"))
    response = client.get(
        f"/api/conversations/{conversation['id']}/messages", headers=bob_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "会话不存在"


def test_unknown_conversation_404(client, make_device):
    device = make_device("alice")
    response = client.get(
        "/api/conversations/not-a-real-id/messages", headers=device["headers"]
    )
    assert response.status_code == 404


def test_conversation_endpoints_require_auth(client):
    assert client.post(
        "/api/conversations", json={"device_id": "x", "title": "x"}
    ).status_code == 401
    assert client.get("/api/conversations/anything/messages").status_code == 401


def test_conversation_owner_is_recorded(app, client, make_device):
    device = make_device("alice")
    conversation = client.post(
        "/api/conversations",
        headers=device["headers"],
        json={"device_id": device["device_id"], "title": "归属"},
    ).json()
    with app.state.db.session() as session:
        stored = session.get(Conversation, conversation["id"])
        assert stored is not None
        assert stored.user_id == device["user_id"]
