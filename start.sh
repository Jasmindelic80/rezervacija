#!/bin/bash
set -e

echo "Pokretanje migracija..."
python manage.py migrate

echo "Kreiranje admin korisnika..."
python manage.py create_default_admin

echo "Učitavanje kategorija..."
python manage.py loaddata fixtures/categories_bih.json || true

echo "Pokretanje servera..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2