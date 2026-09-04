#!/bin/sh
set -e

echo "Waiting for the database..."
python -c "
import time
import sqlalchemy
from app.core.config import settings

for _ in range(30):
    try:
        sqlalchemy.create_engine(settings.database_url).connect().close()
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit('Database is not reachable')
"

if [ -z "$(ls -A alembic/versions 2>/dev/null)" ]; then
    echo "No migrations yet, generating the initial one..."
    alembic revision --autogenerate -m "init"
fi

echo "Applying migrations..."
alembic upgrade head

echo "Starting the API server..."
if [ "$UVICORN_RELOAD" = "1" ]; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
