# Файл: backend/Dockerfile (ИСПРАВЛЕННАЯ ВЕРСИЯ С BULLSEYE)

# --- ЭТАП СБОРКИ ---
# ИЗМЕНЕНИЕ 1: Используем стабильную и проверенную версию Debian "Bullseye"
FROM debian:bullseye-slim as builder

# Устанавливаем ВСЕ системные зависимости, необходимые для WeasyPrint И VENV
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

# Создаем виртуальное окружение
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Копируем и устанавливаем Python-зависимости
COPY requirements.txt .
# Обновляем pip перед установкой, чтобы избежать потенциальных проблем
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt


# --- ЭТАП РАБОТЫ (ФИНАЛЬНЫЙ КОНТЕЙНЕР) ---
# ИЗМЕНЕНИЕ 2: Здесь тоже используем "Bullseye" для консистентности
FROM debian:bullseye-slim

# Устанавливаем только РАБОЧИЕ системные зависимости
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-cffi \
    libcairo2 \
    libpango1.0-0 \
    libgdk-pixbuf2.0-0 \
    # В Bullseye эта библиотека называется libffi7
    libffi7 \
    shared-mime-info \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Копируем виртуальное окружение с установленными пакетами из этапа сборки
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