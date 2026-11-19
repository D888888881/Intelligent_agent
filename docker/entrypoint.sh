#!/bin/sh
set -e

echo "Waiting for database..."
tries=0
until python manage.py shell -c "from django.db import connection; connection.ensure_connection()" 2>/dev/null; do
  tries=$((tries + 1))
  if [ "$tries" -ge 60 ]; then
    echo "Database not ready after 120s"
    exit 1
  fi
  sleep 2
done

python manage.py migrate --noinput

if [ "${RUN_COLLECTSTATIC:-0}" = "1" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"