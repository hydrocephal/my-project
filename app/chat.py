from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import get_db, Message, User
from app.auth import get_current_user, ALGORITHM, SECRET_KEY
from jose import JWTError, jwt
from datetime import datetime
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # active_connections: List of (WebSocket, user_id, username)
        self.active_connections: list[tuple[WebSocket, int, str]] = []

    async def connect(self, websocket: WebSocket, user_id: int, username: str):
        await websocket.accept()
        self.active_connections.append((websocket, user_id, username))
        await self.broadcast({"type": "system", "content": f"{username} joined the chat."})

    def disconnect(self, websocket: WebSocket, username: str):
        # Remove connection from list
        self.active_connections = [c for c in self.active_connections if c[0] != websocket]
        
    async def broadcast(self, message: dict):
        # Clean up closed connections during broadcast
        for connection in self.active_connections:
            try:
                await connection[0].send_json(message)
            except Exception:
                pass # Handle potential disconnects gracefully

    def get_online_users(self):
        return [c[2] for c in self.active_connections]

manager = ConnectionManager()

async def get_user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    
    return db.query(User).filter(User.username == username).first()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str, db: Session = Depends(get_db)):
    user = await get_user_from_token(token, db)
    if user is None:
        await websocket.close(code=4003) # Forbidden
        return

    await manager.connect(websocket, user.id, user.username)
    
    try:
        # Send last 50 messages history
        last_messages = db.query(Message).order_by(Message.timestamp.desc()).limit(50).all()
        for msg in reversed(last_messages):
            # We need to fetch sender name. optimize with join in prod
            sender = db.query(User).filter(User.id == msg.user_id).first()
            sender_name = sender.username if sender else "Unknown"
            await websocket.send_json({
                "type": "message",
                "username": sender_name,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            })

        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("command") == "online":
                online_users = manager.get_online_users()
                await websocket.send_json({
                    "type": "system",
                    "content": f"Online users: {', '.join(online_users)}"
                })
                continue
            
            content = message_data.get("content")
            if content:
                # Save to DB
                new_msg = Message(user_id=user.id, content=content)
                db.add(new_msg)
                db.commit()
                
                # Broadcast
                await manager.broadcast({
                    "type": "message",
                    "username": user.username,
                    "content": content,
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, user.username)
        await manager.broadcast({"type": "system", "content": f"{user.username} left the chat."})
