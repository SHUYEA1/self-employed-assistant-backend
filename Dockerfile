# Dockerfile на основе официальной документации WeasyPrint
# https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#docker

# --- ЭТАП СБОРКИ ---
FROM debian:bookworm-slim as builder

# Устанавливаем ВСЕ системные зависимости, необходимые для WeasyPrint
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-cffi \
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
RUN pip install --no-cache-dir -r requirements.txt


# --- ЭТАП РАБОТЫ (ФИНАЛЬНЫЙ КОНТЕЙНЕР) ---
FROM debian:bookworm-slim

# Устанавливаем только РАБОЧИЕ системные зависимости (без -dev пакетов)
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-cffi \
    libcairo2 \
    libpango1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi8 \
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