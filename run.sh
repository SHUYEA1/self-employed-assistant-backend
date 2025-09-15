#!/bin/bash

# Выход из скрипта, если любая команда завершится с ошибкой
set -e

# Применяем миграции базы данных
python manage.py migrate

# Запускаем Gunicorn веб-сервер
exec gunicorn backend.wsgi:application --bind :$PORT --workers 1 --threads 8 --timeout 0