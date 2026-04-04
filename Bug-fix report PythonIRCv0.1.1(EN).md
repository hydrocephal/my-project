# Bug/fix report  — PythonIRCv0.1.1

## Fixed

1. **Unused function**
   
   - Removed `async def get_current_user` from `auth.py`.  
     This was used for additional token verification; it can be restored if functionality is expanded.

2. **Database Sessions**
   
   - The session is closed after sending the message history (`db.close()`), and a separate session is created for each new message via `SessionLocal()`.

3. **N+1 query in message history**
   
   - `joinedload(Message.sender)` is used to preload users. The loop no longer makes additional database queries.

4. **Dead connections in broadcast_local**
   
   - Updated the `broadcast_local` method to send in parallel via `asyncio.gather()`.
   
   - Disconnected connections are removed from the `active_connections` list.

5. **Race condition during concurrent connection**
   
   - Added `asyncio.Lock()` to `ConnectionManager` to protect `active_connections`.

6. **IntegrityError during registration**
   
   - Handled the exception for a unique username using `try/except` on `db.commit()`.

7. **Removal of unnecessary libraries**
   
   - Only the libraries actually used remain in `requirements.txt`: `fastapi`, `SQLAlchemy`, `requests`, `websockets`, `aioconsole`, `python-jose`, `python-bcrypt`, `pydantic`, `pydantic-settings`.

# Details:

1. In the auth.py file, the `async def get_current_user` function is not used in the code at all; it serves as an additional check for the user's token. 
- Solution: It was removed from the project and left in a draft version for token verification across different commands/requests.

___

2. In the `chat.py` file, within the `async def websocket_endpoint` function, database sessions remain open until the user logs out.
- Solution: An import from `app/db/database.py` was added

```python
from app.db.database import SessionLocal
```

        The session closes after sending the message history

```python
        for msg in reversed(last_messages):

        db.close() 
```

        To save each message to the database, the session is now loaded via import
        python

```python
            if content:
                with SessionLocal() as session:
                    new_msg = Message(user_id=user.id, content=content)
                    session.add(new_msg)
                    session.commit()
```

___

3. N+1 query — in the message history loop
   
   - Solution: Fixed using `from sqlalchemy.orm import joinedload`; it fetches all data at once, including relationships defined in the models—in this case, `Message.sender`.
   
   `joinedload` is applied to the first query to immediately load related data. Then the loop doesn’t make any database queries at all.
   
   python

```python
# Single query — with users included
last_messages = db.query(Message).options(
    joinedload(Message.sender)
).order_by(Message.timestamp.desc()).limit(50).all()

# Loop — no database queries
for msg in reversed(last_messages):
    sender_name = msg.sender.username if msg.sender else “Unknown”
    await websocket.send_json({
        “type”: “message”,
        “username”: sender_name,
        “content”: msg.content,
        “timestamp”: msg.timestamp.isoformat()
    })
```

The line `sender = db.query(User)...` inside the loop is removed entirely — `msg.sender` already contains the user object thanks to `joinedload`.

___

4. Dead connections in broadcast_local — `pass` on an error does not remove the connection from the list.
   The next broadcast_local will attempt to send to it again.
   
   - Solution: Changed sequential sending to parallel using `asyncio.gather` and a loop via a list comprehension, also adding a loop to remove dead connections, which will occur on every call to the `broadcast_local` function

```
    async def broadcast_local(self, message: dict):
        async def send_or_mark_dead(connection):
            try:
                await connection[0].send_json(message)
                return None
            except Exception:
                return connection
        results = await asyncio.gather(*[send_or_mark_dead(c) for c in self.active_connections])
        dead = [c for c in results if c is not None]
        for connection in dead:
            self.active_connections.remove(connection)
```

___

5. In the ConnectionManager class, which contains `self` for accessing objects of this class, there were functions that could create a race condition for the memory of the updated `active_connections` list and overwrite it with false data
   
   - Solution: Added asyncio threading control and placed locks on operations until they complete in the queue using `asyncio.Lock()`

```
   import asyncio
```

```
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[tuple[WebSocket, int, str]] = []
        self._lock = asyncio.Lock()


    async def connect(self, websocket: WebSocket, user_id: int, username: str):
        async with self._lock:
            await websocket.accept()
            self.active_connections.append((websocket, user_id, username))
            await self.broadcast_local({“type”: “system”, ‘content’: f“{username} joined the chat.”})


    async def disconnect(self, websocket: WebSocket):             #add logs with usernames
        async with self._lock:
            self.active_connections = [c for c in self.active_connections if c[0] != websocket]
```

___

6. The project contained unused libraries as well as the less secure `from dotenv import load_dotenv`
   
   - Solution: Unused libraries were removed, including from requirements.txt. `dotenv` was replaced with the more secure `pydantic_settings`, which includes validation and convenience features and is placed in a separate file.

7. There was a section in the auth logic that could potentially cause an `IntegrityError` during simultaneous registration with identical usernames.
   
   - Solution: To address this, the execution order was changed and an exception handler for `IntegrityError` was added to the code.

python

```python
from sqlalchemy.exc import IntegrityError


    try:
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        return None 
```

8. Message timestamps were displayed in the HH:MM:SS format, which was rather inconvenient and pointless for the message history.
   
   - Solution: We changed the format to the more readable DD/MM/YY HH:MM by splitting the strings and making minor adjustments to the client’s CLI code

___

9. A minor bug that doesn’t break anything in the client overall, CancelledError, but could cause problems when scaling and adding functionality.
   
   - Solution: Catch asyncio task exceptions as CancelledError using the line
     
     ```
     await asyncio.gather(*pending, return_exceptions=True)
     ```
     
     after execution
     
     ```
            done, pending = await asyncio.wait(
                [receive_task, send_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
     ```
     
            for task in pending:
                task.cancel()
