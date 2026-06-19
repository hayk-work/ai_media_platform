#!/bin/bash
set -euo pipefail

cd /app/backend/api
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
