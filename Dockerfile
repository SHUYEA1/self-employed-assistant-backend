# Файл: backend/Dockerfile (ФИНАЛЬНАЯ НАДЕЖНАЯ ВЕРСИЯ)

# --- ЭТАП СБОРКИ ---
# Используем стабильную и проверенную версию Debian "Bullseye"
FROM debian:bullseye-slim as builder

# Устанавливаем системные зависимости с дефолтной версией Python 3
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-cffi \
    python3-venv \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Создаем виртуальное окружение с дефолтным python3 (который 3.9)
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Копируем и устанавливаем Python-зависимости
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt


# --- ЭТАП РАБОТЫ (ФИНАЛЬНЫЙ КОНТЕЙНЕР) ---
# Здесь тоже используем "Bullseye"
FROM debian:bullseye-slim

# Устанавливаем РАБОЧИЕ системные зависимости
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-cffi \
    libcairo2 \
    libpango1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi7 \
    shared-mime-info \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Копируем виртуальное окружение с установленными пакетами
COPY --from=builder /venv /venv

# Устанавливаем рабочую директорию и добавляем venv в PATH
WORKDIR /app
ENV PATH="/venv/bin:$PATH"

# Копируем наш код
COPY . .

# Делаем наш скрипт запуска исполняемым
RUN chmod +x /app/run.sh

# Запускаем приложение
EXPOSE 8080
CMD ["/app/run.sh"]