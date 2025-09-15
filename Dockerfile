# Файл: E:\self_employed_assistant\Dockerfile (ФИНАЛЬНАЯ ВЕРСИЯ)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED True
ENV PYTHONDONTWRITEBYTECODE True

WORKDIR /app

# Сначала копируем только requirements.txt для кэширования
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Теперь копируем ВЕСЬ код (все папки) в контейнер
COPY . .

# Команда запуска Gunicorn, указывающая, где найти wsgi файл
CMD exec gunicorn backend.wsgi:application --bind :$PORT --workers 1 --threads 8 --timeout 0