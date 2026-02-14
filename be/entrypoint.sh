#!/bin/bash
set -e

echo "Waiting for database..."
until python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
s.connect(('db', 5432))
s.close()
" 2>/dev/null; do
  echo "  DB not ready, retrying in 2s..."
  sleep 2
done
echo "Database is reachable."

echo "Running Alembic migrations..."
uv run python -c "from alembic.config import main; main(argv=['upgrade', 'heads'])"

echo "Seeding database..."
uv run python -m scripts.seed_data

echo "Starting uvicorn..."
exec uv run uvicorn app.main:create_app --host 0.0.0.0 --port 8080 --factory
