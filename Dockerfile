# Файл: Dockerfile (Финальная ВЕРСИЯ С ПОЛНЫМИ ЗАВИСИМОСТЯМИ)

FROM python:3.11-slim

ENV PYTHONUNBUFFERED True
ENV PYTHONDONTWRITEBYTECODE True

WORKDIR /app

# --- ОБНОВЛЕННЫЙ И ПОЛНЫЙ БЛОК ЗАВИСИМОСТЕЙ ---
# Устанавливаем ВСЕ системные библиотеки, которые могут понадобиться WeasyPrint
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-cffi \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Этот блок у тебя уже был
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/run.sh

EXPOSE 8080
CMD ["/app/run.sh"]