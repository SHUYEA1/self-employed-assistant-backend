# Файл: backend/settings.py (Простая и надежная версия CORS)

from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "localkey_for_development")
DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = ["*"]
# CSRF_TRUSTED_ORIGINS также должен содержать URL фронтенда
CSRF_TRUSTED_ORIGINS = [os.environ.get("FRONTEND_URL", "http://localhost:3000")]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crm',
    'corsheaders', # Библиотека для CORS
    'rest_framework',
    'rest_framework.authtoken',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # --- ГЛАВНОЕ ИЗМЕНЕНИЕ ---
    # corsheaders.middleware.CorsMiddleware ДОЛЖЕН стоять как можно выше, 
    # но ПОСЛЕ SessionMiddleware, если он используется. Это - идеальное место.
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'
TEMPLATES = [ { 'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': { 'context_processors': ['django.template.context_processors.django', 'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages' ], }, }, ]
WSGI_APPLICATION = 'backend.wsgi.application'

DATABASES = {"default": dj_database_url.config(conn_max_age=600, ssl_require=True if os.environ.get("DEBUG") == "False" else False)}

# --- КОНФИГУРАЦИЯ CORS (КАК В ДОКУМЕНТАЦИИ) ---
CORS_ALLOWED_ORIGINS = os.environ.get('FRONTEND_URL', 'http://localhost:3000').split(',')
# Мы используем `CORS_ALLOWED_ORIGINS`, а не `CORS_ORIGIN_WHITELIST` (устаревшее)

# Не будем явно указывать методы и заголовки, библиотека должна справиться сама
# с `CORS_ALLOWED_ORIGINS`.

# --- КОНЕЦ НАСТРОЕК CORS ---

REST_FRAMEWORK = { 'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication', 'rest_framework.authentication.TokenAuthentication'], 'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'] }

AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'ru-ru'; TIME_ZONE = 'UTC'; USE_I18N = True; USE_TZ = True; STATIC_URL = 'static/'; DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'