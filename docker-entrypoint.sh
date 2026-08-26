#!/bin/sh
set -e

# Only one process should run migrations. api and celery_worker share this
# same entrypoint/image and start at roughly the same time (both just wait on
# postgres being healthy) - if both ran `alembic upgrade head` concurrently,
# two racing `CREATE INDEX IF NOT EXISTS` (or any other DDL) statements can
# both pass Postgres's existence check before either commits, and the loser
# crashes with a duplicate-key error on the system catalog, even though the
# SQL says IF NOT EXISTS. RUN_MIGRATIONS=false (set for celery_worker in
# docker-compose.yml) skips this here so only api owns schema migrations.
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
else
    echo "Skipping database migrations (RUN_MIGRATIONS=false)."
fi

if [ "$#" -gt 0 ]; then
    echo "Starting: $*"
    exec "$@"
else
    echo "Starting application..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
