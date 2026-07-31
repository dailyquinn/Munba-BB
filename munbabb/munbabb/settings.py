import os
from pathlib import Path
import sys
from unittest.mock import MagicMock

class MockRedis:
    def ping(self): return True
    def info(self): return {"redis_version": "7.0.0"}
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

class MockDjangoRedis:
    @staticmethod
    def get_redis_connection(*args, **kwargs):
        return MockRedis()

sys.modules['django_redis'] = MockDjangoRedis
sys.modules['django_redis.cache'] = MagicMock()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-dummy-key-replace-me-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'corsheaders',
    'django.contrib.sites',
    'esi',
    'modeltranslation',
    'allianceauth',
    'allianceauth.authentication',
    'allianceauth.services',
    'allianceauth.eveonline',
    'eve_sde',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'munbabb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR.parent], # Point to Repo Root for HTML files
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'munbabb.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DATABASE_PATH', BASE_DIR / 'db.sqlite3'),
    }
}

LANGUAGE_CODE = 'en-us'
LANGUAGES = [('en', 'English')]

TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR.parent] # Serve Repo Root files

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

CORS_ALLOW_ALL_ORIGINS = True

# Reverse Proxy & HTTPS Settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

app_domain_env = (os.getenv("APP_DOMAIN") or "http://localhost:8000").strip()
if app_domain_env and not (app_domain_env.startswith("http://") or app_domain_env.startswith("https://") or app_domain_env.startswith("//")):
    app_domain_env = f"https://{app_domain_env}"

SITE_URL = app_domain_env
CSRF_TRUSTED_ORIGINS = [app_domain_env, 'http://localhost:8000', 'http://127.0.0.1:8000']
if app_domain_env.startswith("https://"):
    raw_domain = app_domain_env.replace("https://", "").rstrip('/')
    CSRF_TRUSTED_ORIGINS.extend([f"https://{raw_domain}", f"http://{raw_domain}", f"https://www.{raw_domain}", f"http://www.{raw_domain}"])

ESI_USER_CONTACT_EMAIL = 'admin@example.com'
LOGIN_TOKEN_SCOPES = ['publicData']
SITE_ID = 1

CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_TASK_DEFAULT_PRIORITY = 5
CELERY_TASK_PRIORITY = 5
CELERY_TASK_DEFAULT_QUEUE = 'celery'
