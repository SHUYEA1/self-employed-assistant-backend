# Файл: backend/settings.py (Версия для дебага)
print("DEBUG: Starting settings.py parsing...")

from pathlib import Path
import os
import dj_database_url
import firebase_admin
from firebase_admin import credentials
import json

print("DEBUG: Basic imports successful.")

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Логируем каждую важную переменную ---
SECRET_KEY = os.environ.get("SECRET_KEY")
print(f"DEBUG: SECRET_KEY is {'SET' if SECRET_KEY else 'NOT SET'}")

DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")

ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://localhost:3000').split(',')
print(f"DEBUG: CSRF_TRUSTED_ORIGINS = {CSRF_TRUSTED_ORIGINS}")

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# ... (INSTALLED_APPS, MIDDLEWARE, ROOT_URLCONF, TEMPLATES, WSGI_APPLICATION)
# Эти блоки редко вызывают проблемы при старте
INSTALLED_APPS = [...]
MIDDLEWARE = [...]
#...


# --- САМОЕ ВАЖНОЕ: Логируем подключение к БД ---
print("DEBUG: Starting database configuration...")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")
print(f"DEBUG: DB_PASSWORD is {'SET' if DB_PASSWORD else 'NOT SET'}")
print(f"DEBUG: DB_NAME is {'SET' if DB_NAME else 'NOT SET'}")

if os.environ.get('K_SERVICE'):
    print("DEBUG: Detected Cloud Run environment (K_SERVICE). Configuring for UNIX socket.")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': '/cloudsql/assistant-saas:europe-west4:assistant-db1',
            'USER': 'postgres',
            'PASSWORD': DB_PASSWORD,
            'NAME': DB_NAME,
        }
    }
else:
    print("DEBUG: No Cloud Run environment detected. Falling back to DATABASE_URL or SQLite.")
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        print("DEBUG: Using DATABASE_URL.")
        DATABASES = {'default': dj_database_url.config(conn_max_age=600)}
    else:
        print("DEBUG: Using fallback SQLite database.")
        DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

print("DEBUG: Database configuration finished.")


# ... (AUTH_PASSWORD_VALIDATORS и т.д.)

# --- Логируем инициализацию Firebase ---
print("DEBUG: Starting Firebase Admin SDK initialization...")
try:
    firebase_creds_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY_JSON')
    if firebase_creds_json:
        print("DEBUG: FIREBASE_SERVICE_ACCOUNT_KEY_JSON is SET.")
        firebase_creds_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(firebase_creds_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            print("DEBUG: Firebase Admin SDK initialized successfully.")
    else:
        print("DEBUG: WARNING! FIREBASE_SERVICE_ACCOUNT_KEY_JSON is NOT SET.")
except Exception as e:
    print(f"DEBUG: FATAL ERROR during Firebase init: {e}")
    # Вызываем исключение, чтобы контейнер точно упал с этим сообщением
    raise e

print("DEBUG: settings.py parsing finished successfully.")