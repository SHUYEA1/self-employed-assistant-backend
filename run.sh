#!/bin/bash

# Выходим сразу, если любая команда завершится с ошибкой
set -e

# Применяем миграции базы данных
echo "Applying database migrations..."
python manage.py migrate

# Запускаем Gunicorn.
# Ключевое изменение: --bind "0.0.0.0:${PORT}"
# Это заставит Gunicorn слушать порт, указанный Cloud Run.
echo "Starting Gunicorn server..."
gunicorn backend.wsgi:application --bind "0.0.0.0:${PORT}"