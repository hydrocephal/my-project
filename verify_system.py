import asyncio
import requests
import websockets
import json
import sys

API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"

async def register_and_login(username, password):
    print(f"[{username}] Registering...")
    requests.post(f"{API_URL}/auth/register", json={"username": username, "password": password})
    
    print(f"[{username}] Logging in...")
    resp = requests.post(f"{API_URL}/auth/token", data={"username": username, "password": password})
    if resp.status_code != 200:
        raise Exception(f"Login failed for {username}: {resp.text}")
    return resp.json()["access_token"]

async def test_scenario():
    print("--- Starting Verification ---")
    
    token1 = await register_and_login("user1", "pass123")
    token2 = await register_and_login("user2", "pass123")

    async with websockets.connect(f"{WS_URL}?token={token1}") as ws1, \
               websockets.connect(f"{WS_URL}?token={token2}") as ws2:
        
        print("\n[System] Both users connected.")

        # Consume join messages
        await ws1.recv() # user1 joined
        await ws2.recv() # user1 joined (history) or user2 joined? 
        # Actually join messages are broadcast. 
        # When ws2 connects, ws1 receives "user2 joined".
        # We need to be careful with exact sequence, so we'll just read loop until we find what we want.

        print("[User1] Sending 'Hello User2'")
        await ws1.send(json.dumps({"content": "Hello User2"}))

        print("[User2] Waiting for message...")
        while True:
            msg = json.loads(await ws2.recv())
            if msg.get("type") == "message" and msg.get("content") == "Hello User2":
                print(f"[User2] Received: {msg['content']} from {msg['username']}")
                break
        
        print("[User2] Sending 'Hi User1'")
        await ws2.send(json.dumps({"content": "Hi User1"}))

        print("[User1] Waiting for message...")
        while True:
            msg = json.loads(await ws1.recv())
            if msg.get("type") == "message" and msg.get("content") == "Hi User1":
                print(f"[User1] Received: {msg['content']} from {msg['username']}")
                break
        
        print("[User1] Checking online users...")
        await ws1.send(json.dumps({"command": "online"}))
        while True:
            msg = json.loads(await ws1.recv())
            print(f"[User1] Msg: {msg}")
            if msg.get("type") == "system" and "user1" in msg.get("content") and "user2" in msg.get("content"):
                print(f"[User1] Online check pass: {msg['content']}")
                break

    print("\n--- Verification Passed ---")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_scenario())
