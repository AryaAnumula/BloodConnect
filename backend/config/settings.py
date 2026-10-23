"""Provisional LOCAL starter settings; see docs/decisions.md before feature work."""
from pathlib import Path
import os
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / '.env', override=False)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if len(SECRET_KEY) < 40 or SECRET_KEY.startswith('CHANGE_ME'):
    raise ImproperlyConfigured('Generate a local DJANGO_SECRET_KEY with scripts/bootstrap_env.py.')
DEBUG = os.environ.get('DJANGO_DEBUG', '0') == '1'
ALLOWED_HOSTS = [x.strip() for x in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if x.strip()]
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.staticfiles', 'rest_framework', 'accounts', 'donors', 'audit', 'notification_adapter', 'core']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'core.middleware.RequestIDMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware']
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'frontend/templates'], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth']}}]
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'frontend/static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
if os.environ.get('DB_ENGINE', 'postgresql') == 'sqlite':
    if os.environ.get('ALLOW_SQLITE_SMOKE', '0') != '1':
        raise ImproperlyConfigured('SQLite is permitted only with explicit ALLOW_SQLITE_SMOKE=1 for scaffold smoke tests.')
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'local-smoke.sqlite3'}}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': os.environ.get('POSTGRES_DB', 'bloodconnect'), 'USER': os.environ.get('POSTGRES_USER', 'bloodconnect'), 'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''), 'HOST': os.environ.get('POSTGRES_HOST', '127.0.0.1'), 'PORT': os.environ.get('POSTGRES_PORT', '5432'), 'CONN_MAX_AGE': 0}}
AUTH_USER_MODEL = 'accounts.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
APPEND_SLASH = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = os.environ.get('DJANGO_SECURE_COOKIES', '0') == '1'
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 1800  # PROVISIONAL inactivity/session policy: approval required.
SESSION_SAVE_EVERY_REQUEST = False
CSRF_FAILURE_VIEW = 'core.errors.csrf_failure'
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'], 'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'], 'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'], 'EXCEPTION_HANDLER': 'core.errors.exception_handler', 'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser']}
# No CORS wildcard: frontend and backend share an origin.
