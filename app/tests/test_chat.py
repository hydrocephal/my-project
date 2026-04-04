from app.schemas.auth import UserCreate
from app.services.auth import create_access_token, create_user
from app.services.chat import get_user_from_token


async def test_user_from_token(db):
    user_data = UserCreate(username="GenaPupkin", password="secretpass")
    await create_user(user_data, db)

    token = create_access_token(data={"sub": "GenaPupkin"})
    result = await get_user_from_token(token, db)
    assert result is not None
    assert result.username == "GenaPupkin"


async def test_websocket_connect(sync_client):
    sync_client.post("/auth/register", json={"username": "GenaPupkin", "password": "secretpass"})
    response = sync_client.post("/auth/token", data={"username": "GenaPupkin", "password": "secretpass"})

    token = response.json()["access_token"]

    with sync_client.websocket_connect("/ws") as ws:
        ws.send_json({"token": token})
        data = ws.receive_json()
        print(f"{data}")
        assert data["type"] == "system"
        assert "GenaPupkin" in data["content"]


async def test_websocket_online(sync_client):
    sync_client.post("/auth/register", json={"username": "GenaPupkin", "password": "secretpass"})
    response = sync_client.post("/auth/token", data={"username": "GenaPupkin", "password": "secretpass"})

    token = response.json()["access_token"]

    with sync_client.websocket_connect("/ws") as ws:
        ws.send_json({"token": token})
        ws.receive_json()

        ws.send_json({"command": "online"})
        data = ws.receive_json()
    print(data)
    assert data["type"] == "system"
    assert "GenaPupkin" in data["content"]


async def test_message(sync_client):
    sync_client.post("/auth/register", json={"username": "GenaPupkin", "password": "secretpass"})
    response = sync_client.post("/auth/token", data={"username": "GenaPupkin", "password": "secretpass"})

    token1 = response.json()["access_token"]

    sync_client.post("/auth/register", json={"username": "Eblan", "password": "Eblan"})
    response = sync_client.post("/auth/token", data={"username": "Eblan", "password": "Eblan"})

    token2 = response.json()["access_token"]

    with sync_client.websocket_connect("/ws") as ws1, sync_client.websocket_connect("/ws") as ws2:
        ws1.send_json({"token": token1})
        ws1.receive_json()

        ws2.send_json({"token": token2})
        ws2.receive_json()
        ws1.receive_json()

        ws1.send_json({"content": "See ya champ"})

        message = ws2.receive_json()
        print(message)
    assert "See ya champ" in message["content"]


async def test_disconnect_reconnect_history(sync_client):
    sync_client.post("/auth/register", json={"username": "GenaPupkin", "password": "secretpass"})
    response = sync_client.post("/auth/token", data={"username": "GenaPupkin", "password": "secretpass"})

    token1 = response.json()["access_token"]

    sync_client.post("/auth/register", json={"username": "Eblan", "password": "Eblan"})
    response = sync_client.post("/auth/token", data={"username": "Eblan", "password": "Eblan"})

    token2 = response.json()["access_token"]

    with sync_client.websocket_connect("/ws") as ws1, sync_client.websocket_connect("/ws") as ws2:
        ws1.send_json({"token": token1})
        ws1.receive_json()
        ws1.send_json({"content": "See ya champ"})
        ws1.receive_json()

        ws2.send_json({"token": token2})
        ws2.receive_json()
        ws1.receive_json()
        ws2.receive_json()

        ws1.close()
        left = ws2.receive_json()
        print(left)
    assert "GenaPupkin left the chat" in left["content"]

    with sync_client.websocket_connect("/ws") as ws1:
        ws1.send_json({"token": token1})
        ws1.receive_json()
        history = ws1.receive_json()
        print(history)
    assert "See ya champ" in history["content"]
