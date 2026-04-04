# Ghost IRC — Bug Fix Report

---

### Premature DB session close during history streaming
`chat.py → websocket_connection_logic()`

`db.close()` вызывался внутри цикла отправки истории. Сессия убивалась до того как цикл заканчивался, что могло привести к `DetachedInstanceError` при обращении к атрибутам объектов SQLAlchemy после закрытия.

**Fix:** история, аутентификация и сохранение сообщений теперь каждый в своём `with SessionLocal()` блоке — сессия живёт ровно столько сколько нужно и закрывается автоматически.

---

### Broadcast_local sent before guaranteed DB commit
`chat.py → message receive loop`

`broadcast_local()` находился снаружи `try` блока — если `commit()` падал с исключением, сообщение всё равно уходило всем пользователям, хотя в базе его не было.

**Fix:** `broadcast_local()` перенесён внутрь `try`, после `commit()`. При любом исключении вызывается `session.rollback()` и broadcast_local не выполняется.

---

### Race condition in ConnectionManager.broadcast_local()
`chat.py → ConnectionManager.broadcast_local()`

`asyncio.gather()` вызывался внутри лока — это значит что пока шла отправка всем пользователям, новые подключения не могли добавиться в список, они просто висели и ждали.

**Fix:** лок захватывается только для копирования списка соединений и для удаления мёртвых. Отправка идёт снаружи лока.

---

### JWT token passed via WebSocket URL
`cli.py + chat.py`

Токен передавался как `?token=...` в URL WebSocket соединения. URL целиком пишется в логи сервера при каждом подключении — токен оказывался в открытом виде в логах.

**Fix:** токен отправляется первым JSON сообщением сразу после установки соединения. Сервер читает его через `receive_text()` до начала основной логики.

---

### Wrong string in "left the chat" name extraction
`cli.py → receive_messages()`

Сервер отправлял строку без точки в конце, а клиент пытался вырезать подстроку с точкой — из-за несовпадения имя пользователя никогда не извлекалось корректно и в системное сообщение уходила вся строка целиком.

**Fix:** сервер и клиент приведены к одному виду — строка с точкой на обоих концах.

---

### DateTime column missing timezone=True
`models.py → Message.timestamp`

Колонка была определена как `DateTime` без `timezone=True`, но дефолтное значение использовало `datetime.now(timezone.utc)` — timezone-aware объект. SQLite сохранял его как naive datetime, теряя UTC offset, что приводило к некорректному сравнению времён.

**Fix:** колонка изменена на `DateTime(timezone=True)` — offset теперь сохраняется и корректно восстанавливается при чтении.
