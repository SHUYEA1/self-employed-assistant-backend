# Файл: Dockerfile (Финальная чистая версия)

FROM python:3.11-slim

ENV PYTHONUNBUFFERED True
ENV PYTHONDONTWRITEBYTECODE True

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Делаем наш стартовый скрипт исполняемым внутри контейнера
RUN chmod +x /app/run.sh

# Запускаем наш стартовый скрипт
CMD ["/app/run.sh"]