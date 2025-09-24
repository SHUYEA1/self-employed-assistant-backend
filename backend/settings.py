# Файл: backend/settings.py (Финальная версия для Cloud Run / Cloud Shell)

from pathlib import Path
import os
import dj_database_url
import firebase_admin
from firebase_admin import credentials
import json

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY") # <-- Теперь это обязательная переменная
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://localhost:3000').split(',')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crm',
    'corsheaders',
    'rest_framework',
    'rest_framework.authtoken',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'backend.urls'
TEMPLATES = [
    {'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True,
     'OPTIONS': {'context_processors': ['django.template.context_processors.debug', 'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}
]
WSGI_APPLICATION = 'backend.wsgi.application'

# --- НОВЫЙ, УМНЫЙ КОНФИГ ДЛЯ БАЗЫ ДАННЫХ ---
# Проверяем, запущено ли приложение в среде Google Cloud (Cloud Run, Cloud Shell)
# В Cloud Run переменная K_SERVICE установлена автоматически.
if os.environ.get('K_SERVICE'):
    # Подключение для Cloud Run / Cloud Shell через UNIX socket
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': '/cloudsql/assistant-saas:europe-west4:assistant-db1', # <-- ПУТЬ К СОКЕТУ
            'USER': 'postgres', 
            # ВАЖНО: Пароль и имя БД теперь тоже берутся из переменных окружения
            'PASSWORD': os.environ.get("DB_PASSWORD"), 
            'NAME': os.environ.get("DB_NAME", "postgres"),
        }
    }
else:
    # Конфигурация для локальной разработки (через localhost:5432)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        DATABASES = {'default': dj_database_url.config(conn_max_age=600)}
    else:
        # Резервный вариант для локальной работы, если ничего не настроено
        DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}


SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = not DEBUG
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- ЕДИНЫЙ БЛОК REST_FRAMEWORK ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication'
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100
}

CORS_ALLOW_ALL_ORIGINS = True

# --- БЛОК ИНИЦИАЛИЗАЦИИ FIREBASE ADMIN SDK (без изменений) ---
try:
    firebase_creds_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY_JSON')
    if firebase_creds_json:
        firebase_creds_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(firebase_creds_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
except Exception as e:
    print(f"ERROR: Failed to initialize Firebase Admin SDK: {e}")