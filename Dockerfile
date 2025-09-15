# Файл: E:\self_employed_assistant\Dockerfile (ФИНАЛЬНАЯ ВЕРСИЯ v2)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED True
ENV PYTHONDONTWRITEBYTECODE True

WORKDIR /app

# --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
# requirements.txt лежит в корне, рядом с Dockerfile, поэтому путь не нужен
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код в контейнер
COPY . .

# Команда запуска
CMD exec gunicorn backend.wsgi:application --bind :$PORT --workers 1 --threads 8 --timeout 0