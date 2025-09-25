#!/bin/bash
set -e
python manage.py migrate
exec gunicorn backend.wsgi:application --bind "0.0.0.0:${PORT}"