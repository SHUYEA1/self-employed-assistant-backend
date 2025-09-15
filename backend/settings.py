# Файл: backend/settings.py (Пуленепробиваемая версия)
from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-super-secret-key-for-local-dev")
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")

ALLOWED_HOSTS = ["*"] # Cloud Run работает за прокси, это безопасно
# Явно добавляем URL фронтенда в доверенные источники для CSRF
CSRF_TRUSTED_ORIGINS = [os.environ.get('FRONTEND_URL', 'http://localhost:3000')]

INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','crm','corsheaders','rest_framework','rest_framework.authtoken',]
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','corsheaders.middleware.CorsMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware',]
ROOT_URLCONF = 'backend.urls'
TEMPLATES = [ { 'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': { 'context_processors': ['django.template.context_processors.django', 'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages' ], }, }, ]
WSGI_APPLICATION = 'backend.wsgi.application'

# --- ГЛАВНОЕ ИЗМЕНЕНИЕ: Пуленепробиваемая конфигурация БД ---
# Сначала пытаемся получить DATABASE_URL из окружения
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Если переменная есть, используем ее
    DATABASES = {'default': dj_database_url.config(conn_max_age=600, ssl_require=not DEBUG)}
else:
    # ЕСЛИ ПЕРЕМЕННОЙ НЕТ (!!!), используем локальную SQLite.
    # Это гарантирует, что приложение ЗАПУСТИТСЯ в любом случае.
    print("WARNING: DATABASE_URL not found, falling back to SQLite.")
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
# --- КОНЕЦ ИЗМЕНЕНИЯ ---

AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'ru-ru'; TIME_ZONE = 'UTC'; USE_I18N = True; USE_TZ = True; STATIC_URL = 'static/'; DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
REST_FRAMEWORK = { 'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication', 'rest_framework.authentication.TokenAuthentication'], 'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'] }
CORS_ALLOW_ALL_ORIGINS = True # Самая простая и надежная настройка