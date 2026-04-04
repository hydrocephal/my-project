# Bug/fix report — PythonIRCv0.1.1

## Исправлено

1. **Неиспользуемая функция**
   
   - Удалена `async def get_current_user` из `auth.py`.  
     Служила для дополнительной проверки токена, можно вернуть при расширении функционала.

2. **Сессии базы данных**
   
   - Закрытие сессии после отправки истории сообщений (`db.close()`) и для каждого нового сообщения создаётся отдельная сессия через `SessionLocal()`.

3. **N+1 запрос в истории сообщений**
   
   - Использован `joinedload(Message.sender)` для предзагрузки пользователей. Цикл теперь не делает дополнительных запросов к БД.

4. **Мёртвые соединения в broadcast_local**
   
   - Обновлён метод `broadcast_local` на параллельную отправку через `asyncio.gather()`.
   
   - Отвалившиеся соединения удаляются из списка `active_connections`.

5. **Race condition при concurrent connect**
   
   - Добавлен `asyncio.Lock()` в `ConnectionManager` для защиты `active_connections`.

6. **IntegrityError при регистрации**
   
   - Обработка исключения для уникального username через `try/except` на `db.commit()`.

7. **Удаление лишних библиотек**
   
   - В `requirements.txt` остались только реально используемые: `fastapi`, `SQLAlchemy`, `requests`, `websockets`, `aioconsole`, `python-jose`, `python-bcrypt`, `pydantic`, `pydantic-settings`.

# Детально:

1. В файле auth.py функция async def get_current_user не используется в коде вообще, она служит для дополнительной проверки токена пользователя.
- Решение: Была удалена из проекта и оставлена в черновом варианте для проверки токена при разных командах/запросах.

---

2. В файле chat.py в функции async def websocket_endpoint сессии с базой данных остаются висеть пока пользователь не отключится.
   
   - Решение: Был добавлен импорт из `app/db/database.py` python

```python
from app.db.database import SessionLocal
```

```
    сессия закрывается после отправки истории сообщений
```

```python
        for msg in reversed(last_messages):

        db.close() 
```

```
    для сохранения каждого сообщения в базу теперь подтягивается сессия через импорт
    python
```

```python
            if content:
                with SessionLocal() as session:
                    new_msg = Message(user_id=user.id, content=content)
                    session.add(new_msg)
                    session.commit()
```

---

3. N+1 запрос — в цикле истории сообщений
   
   - Решение: Пофикшен с помощью `from sqlalchemy.orm import joinedload` он подтягивает сразу все данные включая relationship прописанные в models здесь именно Message.sender
   
   `joinedload` ставится на первый запрос чтобы сразу подгрузить связанные данные. Тогда цикл вообще не делает запросов к БД.
   
   python

```python
# Один запрос — сразу с юзерами
last_messages = db.query(Message).options(
    joinedload(Message.sender)
).order_by(Message.timestamp.desc()).limit(50).all()

# Цикл — без запросов к БД
for msg in reversed(last_messages):
    sender_name = msg.sender.username if msg.sender else "Unknown"
    await websocket.send_json({
        "type": "message",
        "username": sender_name,
        "content": msg.content,
        "timestamp": msg.timestamp.isoformat()
    })
```

Строчка `sender = db.query(User)...` внутри цикла удаляется полностью — `msg.sender` уже содержит объект юзера благодаря `joinedload`.

---

4. Мёртвые соединения в broadcast_local — `pass` при ошибке не удаляет соединение из списка.  
   Следующий broadcast_local снова попытается туда отправить.
   
   - Решение: Последовательную отправку изменил на параллельную с помощью asyncio.gather и цикла через сокращение list comprehension также добавив цикл для удаления мертвых соединений который будет будет происходить при каждом вызове функции broadcast_local

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

---

5. В классе ConnectionManager который содержит в себе self для обращения к объектам этого класса были функции которые могут создать конкурентность race condition для памяти обновляемого списка active_connections и перезаписывать его ложными данными
   
   - Решение: Добавлено управление потоком asyncio и расставлены блокировки операций до их завершения в очереди с помощью `asyncio.Lock()`

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
            await self.broadcast_local({"type": "system", "content": f"{username} joined the chat."})


    async def disconnect(self, websocket: WebSocket):             #add logs with usernames
        async with self._lock:
            self.active_connections = [c for c in self.active_connections if c[0] != websocket]
```

---

6. В проекте находились неиспользуемые библиотеки а также менее безопасный from dotenv import load_dotenv
   
   - Решение: Неиспользуемые библиотеки удалены, в том числе из requirements.txt. Произведена замена dotenv на более безопасный pydantic_settings с валидацией и удобствами, который размещен в отдельном файле.

7. В логике auth находилось место которое потенциально могло вызвать `IntegrityError` при одновременной регистрации с одинаковыми никами.
   
   - Решение: На такой случай был изменен порядок выполнения и добавлено исключение в коде для `IntegrityError`

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

8. Время сообщений отображалось в формате HH:MM:SS что довольно неудобно и бессмысленно для истории сообщений.
   
   - Решение: Заменили формат на читаемый DD/MM/YY HH:MM с помощью разделения строк и небольших манипуляций с кодом CLI клиента

---

9. Незначительный баг который в целом ничего не ломает в клиенте, CancelledError, но при масштабировании и добавлении функционала мог бы создать проблемы.
   
   - Решение: Ловить исключения задач asyncio в виде CancelledError через строчку
   
   ```
   await asyncio.gather(*pending, return_exceptions=True)
   ```
   
   после выполнения

```python
            done, pending = await asyncio.wait(
                [receive_task, send_task],
                return_when=asyncio.FIRST_COMPLETED,
            )


            for task in pending:
                task.cancel()
```
