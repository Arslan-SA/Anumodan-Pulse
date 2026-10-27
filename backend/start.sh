#!/usr/bin/env bash
set -e

echo "=== AICTE FlowOps Production Startup ==="
echo "Running database schema migrations via Alembic..."
alembic upgrade head

echo "Starting Uvicorn ASGI server..."
PORT="${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 2
