from tests.conftest import register


async def test_register_login_and_me(client):
    headers = await register(client)
    me = await client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "farmer@example.com"

    login = await client.post("/auth/login", json={"email": "FARMER@example.com", "password": "correct-horse"})
    assert login.status_code == 200
    assert login.json()["user"]["name"] == "Farmer"


async def test_duplicate_email_rejected(client):
    await register(client)
    response = await client.post(
        "/auth/register", json={"email": "farmer@example.com", "name": "X", "password": "another-pass"}
    )
    assert response.status_code == 409


async def test_wrong_password_and_missing_token(client):
    await register(client)
    bad = await client.post("/auth/login", json={"email": "farmer@example.com", "password": "nope-nope"})
    assert bad.status_code == 401
    assert (await client.get("/conversations")).status_code == 401
    assert (await client.get("/conversations", headers={"Authorization": "Bearer junk"})).status_code == 401
