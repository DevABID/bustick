#!/usr/bin/env bash
# Render runs this on every deploy (Build Command: ./build.sh)
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Admin login from env vars (DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD). Skipped if it already exists.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python manage.py createsuperuser --no-input || echo "Admin user already exists."
fi

# Demo routes, buses and trips (set SEED_DEMO=True). Safe to run repeatedly.
if [ "$SEED_DEMO" = "True" ]; then
  python manage.py seed_demo
fi

# Keep trips on sale for the next 30 days (repeats existing departures)
python manage.py extend_schedules --days 30
