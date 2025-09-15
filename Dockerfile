# Файл: Dockerfile (Финальная версия с run.sh)
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
```**Шаг 4: Последний деплой**
1.  Отправь все изменения на GitHub:
    ```bash
    # (в терминале для бэкенда)
    git add .
    git commit -m "feat: Add entrypoint script to run migrations"
    git push
    ```
2.  Google Cloud Build **автоматически** подхватит изменения, соберет новый образ и задеплоит его.

### Итог
После того как новый деплой завершится:
*   Новый контейнер запустится.
*   Он первым делом выполнит скрипт `run.sh`.
*   Скрипт выполнит `python manage.py migrate`, и в твоей PostgreSQL базе **создадутся все таблицы**.
*   Сразу после этого скрипт запустит Gunicorn.

Теперь, когда ты попробуешь зарегистрироваться, `RegisterSerializer` найдет таблицу `auth_user`, успешно создаст пользователя, и ты **увидишь свое приложение**.

**Мы у финишной черты.** Это был последний шаг.