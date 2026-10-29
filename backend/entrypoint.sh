#!/bin/sh
set -e

echo "Applying database migrations with Alembic..."
alembic upgrade head

echo "Starting FastAPI server..."
exec "$@"
