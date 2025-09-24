# Файл: Dockerfile (Финальная ИСПРАВЛЕННАЯ версия)

FROM python:3.11-slim

ENV PYTHONUNBUFFERED True
ENV PYTHONDONTWRITEBYTECODE True

WORKDIR /app

# --- ДОБАВЛЕННЫЙ БЛОК ---
# Обновляем менеджер пакетов и устанавливаем системные зависимости для WeasyPrint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libgobject-2.0-0 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Этот блок у тебя уже был
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/run.sh

# Запускаем наш стартовый скрипт (добавил EXPOSE для ясности)
EXPOSE 8080
CMD ["/app/run.sh"]