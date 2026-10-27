from tests.conftest import register
from tests.fakes import jpeg_bytes


async def test_conversation_crud_and_isolation(client):
    alice = await register(client, "alice@example.com")
    bob = await register(client, "bob@example.com")

    created = await client.post("/conversations", json={}, headers=alice)
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    assert created.json()["title"] == "New conversation"

    renamed = await client.patch(f"/conversations/{conversation_id}", json={"title": "Tomatoes"}, headers=alice)
    assert renamed.json()["title"] == "Tomatoes"

    listed = await client.get("/conversations", headers=alice)
    assert [c["id"] for c in listed.json()] == [conversation_id]
    assert (await client.get("/conversations", headers=bob)).json() == []
    assert (await client.get(f"/conversations/{conversation_id}", headers=bob)).status_code == 404

    detail = await client.get(f"/conversations/{conversation_id}", headers=alice)
    assert detail.json()["messages"] == []

    assert (await client.delete(f"/conversations/{conversation_id}", headers=alice)).status_code == 204
    assert (await client.get(f"/conversations/{conversation_id}", headers=alice)).status_code == 404


async def test_upload_roundtrip_and_ownership(client):
    alice = await register(client, "alice@example.com")
    bob = await register(client, "bob@example.com")
    png = jpeg_bytes()
    response = await client.post("/uploads", files={"image": ("leaf.jpg", png, "image/jpeg")}, headers=alice)
    assert response.status_code == 201
    upload_id = response.json()["id"]

    assert (await client.get(f"/uploads/{upload_id}", headers=alice)).content == png
    assert (await client.get(f"/uploads/{upload_id}", headers=bob)).status_code == 404

    rejected = await client.post("/uploads", files={"image": ("x.txt", b"hi", "text/plain")}, headers=alice)
    assert rejected.status_code == 415
    corrupt = await client.post("/uploads", files={"image": ("x.jpg", b"\xff\xd8junk", "image/jpeg")}, headers=alice)
    assert corrupt.status_code == 415


async def test_send_message_without_llm_returns_503(client):
    headers = await register(client)
    conversation_id = (await client.post("/conversations", json={}, headers=headers)).json()["id"]
    response = await client.post(f"/conversations/{conversation_id}/messages", json={"text": "hi"}, headers=headers)
    assert response.status_code == 503


async def test_timestamps_are_serialized_as_utc(client):
    headers = await register(client)
    created = (await client.post("/conversations", json={}, headers=headers)).json()
    listed = (await client.get("/conversations", headers=headers)).json()
    assert created["updated_at"].endswith("Z") or created["updated_at"].endswith("+00:00")
    assert listed[0]["updated_at"].endswith("Z") or listed[0]["updated_at"].endswith("+00:00")
