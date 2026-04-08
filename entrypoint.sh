#!/bin/sh
alembic upgrade head
exec gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000