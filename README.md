**GhostChat — IRC-style Chat**

A real-time IRC-style chat application built with FastAPI, WebSockets, and SQLite.

---

**Stack**

- FastAPI + WebSockets
- SQLAlchemy + SQLite
- JWT authentication (python-jose)
- bcrypt password hashing
- asyncio CLI client

---

**Requirements**

- Python 3.10+

---

**Installation**

Clone the repository:

bash

```bash
git clone https://github.com/hydrocephal/PythonIRC.git
cd PythonIRC
```

Create and activate virtual environment:

bash

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

Install dependencies:

bash

```bash
pip install -r requirements.txt
```

Create `.env` file from example:

bash

```bash
cp .env.example .env
```

---

**Configuration**

Edit `.env`:
```
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./irc_chat.db
```

---

**Running**

Start the server:

bash

```bash
uvicorn app.main:app --reload
```

In a separate terminal, start the client:

bash

```bash
python client/cli.py
```

---

**Usage**
```
1. Register a new account or login
2. Start chatting

Commands:
  /online   — show online users
  /exit     — disconnect from chat
```

---

**Project Structure**
```
app/
  core/         — configuration
  db/           — database connection
  models/       — SQLAlchemy models
  routers/      — HTTP and WebSocket endpoints
  services/     — business logic
  schemas/      — Pydantic schemas
  main.py       — application entry point
client/
  cli.py        — terminal chat client
```
