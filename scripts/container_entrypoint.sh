#!/bin/sh
set -eu

echo "[entrypoint] applying database migrations"
alembic upgrade head

echo "[entrypoint] starting bot"
exec python -m app.main
