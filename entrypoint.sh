#!/bin/sh
/app/.venv/bin/alembic upgrade head
exec /app/.venv/bin/gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000