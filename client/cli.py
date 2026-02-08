import asyncio
import requests
import websockets
import aioconsole
import json
import sys
import os
import getpass

API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Enable ANSI escape codes on Windows 10/11
if os.name == 'nt':
    os.system('')

def get_auth_token():
    print("Welcome to IRC Chat MVP!")
    while True:
        choice = input("1. Login\n2. Register\nChoose (1/2): ").strip()
        
        if choice == '2':
            username = input("Enter new username: ").strip()
            password = getpass.getpass("Enter new password: ").strip()
            try:
                response = requests.post(
                    f"{API_URL}/auth/register",
                    json={"username": username, "password": password}
                )
                if response.status_code == 200:
                    print("Registration successful! Please login.")
                else:
                    print(f"Error: {response.json().get('detail', 'Registration failed')}")
            except requests.exceptions.ConnectionError:
                print("Error: Could not connect to server. Is it running?")
                return None

        elif choice == '1':
            username = input("Username: ").strip()
            password = getpass.getpass("Password: ").strip()
            try:
                response = requests.post(
                    f"{API_URL}/auth/token",
                    data={"username": username, "password": password}
                )
                if response.status_code == 200:
                    token_data = response.json()
                    return token_data["access_token"], username
                else:
                    print("Login failed: Invalid credentials")
            except requests.exceptions.ConnectionError:
                print("Error: Could not connect to server. Is it running?")
                return None
        else:
            print("Invalid choice.")

async def receive_messages(websocket, username):
    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "message":
                sender = data.get("username", "Unknown")
                content = data.get("content", "")
                timestamp = data.get("timestamp", "")
                # Format timestamp nicely (HH:MM:SS) if possible, else raw
                try:
                    ts = timestamp.split("T")[1].split(".")[0]
                except:
                    ts = timestamp
                
                if sender == username:
                    print(f"[{ts}] You: {content}")
                else:
                    print(f"[{ts}] {sender}: {content}")
            
            elif msg_type == "system":
                print(f"[SYSTEM] {data.get('content')}")

    except websockets.exceptions.ConnectionClosed:
        print("\nConnection closed by server.")

async def send_messages(websocket):
    while True:
        try:
            message = await aioconsole.ainput("")
            if not message.strip():
                continue
                
            if message.strip() == "/exit":
                print("Exiting...")
                await websocket.close()
                break
            
            if message.strip() == "/online":
                 await websocket.send(json.dumps({"command": "online"}))
                 continue

            # Clear line after sending (cosmetic)
            # \033[F = Move cursor up one line
            # \033[K = Clear line from cursor to end
            # This deletes the user's typed input line so it can be replaced by the server's formatted message
            sys.stdout.write("\033[F\033[K")
            sys.stdout.flush()
            
            await websocket.send(json.dumps({"content": message}))
        except (EOFError, KeyboardInterrupt):
            await websocket.close()
            break

async def start_chat(token, username):
    print(f"\nConnecting as {username}...")
    uri = f"{WS_URL}?token={token}"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Type messages and press Enter.")
            print("Commands: /online, /exit")
            print("--- Chat History ---")
            
            receive_task = asyncio.create_task(receive_messages(websocket, username))
            send_task = asyncio.create_task(send_messages(websocket))
            
            done, pending = await asyncio.wait(
                [receive_task, send_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            
            for task in pending:
                task.cancel()
                
    except Exception as e:
        print(f"Connection failed: {e}")

def main():
    auth_result = get_auth_token()
    if auth_result:
        token, username = auth_result
        try:
            print("Starting chat client...")
            # Windows SelectorEventLoop policy fix for Python 3.8+
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            asyncio.run(start_chat(token, username))
        except KeyboardInterrupt:
            print("\nGoodbye!")

if __name__ == "__main__":
    main()
