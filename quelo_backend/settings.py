"""
Django settings for quelo_backend project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from core.utils.aws_secrets import get_secret
import logging

# Load .env
load_dotenv()

# -----------------------------
# Hosts & Security
# -----------------------------

ALLOWED_HOSTS = [
    "quelo.in", 
    "www.quelo.in",
    "localhost", 
    "127.0.0.1",
    ".elasticbeanstalk.com",
]

APPEND_SLASH = True

CSRF_TRUSTED_ORIGINS = [
    "https://quelo.in",
    "https://www.quelo.in",
    "https://*.elasticbeanstalk.com",
    ]

# Trust the load balancer’s HTTPS header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 0


# Toggle these via environment variables
# SECURE_SSL_REDIRECT   = os.getenv("SECURE_SSL_REDIRECT", "false").lower() == "true"
SECURE_SSL_REDIRECT   = False
SESSION_COOKIE_SECURE = True # os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
CSRF_COOKIE_SECURE    = True # os.getenv("CSRF_COOKIE_SECURE", "false").lower() == "true"

# Exempt health check from HTTPS redirection
SECURE_REDIRECT_EXEMPT = [r"^health/?$"]

# Use LB’s forwarded host for correct domain resolution
USE_X_FORWARDED_HOST = True


BASE_DIR = Path(__file__).resolve().parent.parent
LOGIN_URL = '/login/'


DEBUG = True
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")

# -----------------------------
# AWS S3 Storage
# -----------------------------

# Media (user uploads)
# -----------------------------
# Apps
# -----------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "patients",
    "queue_mgt",
    "doctors",
    "services",
    "appointments",
    "billing",
    "prescription",
    "drugs",
    "reports",
    "vitals",
    "widget_tweaks",
    "core.apps.CoreConfig",
    "whatsapp_notifications",
    "hospital_admin",
    "hospital_portal",
    "visit_workspace",
]

# -----------------------------
# Middleware
# -----------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# -----------------
# Static & Media Storage (S3)
AWS_S3_REGION_NAME = "ap-south-1"

AWS_DEFAULT_ACL = None  # prevent django-storages from trying to set ACLs
AWS_QUERYSTRING_AUTH = False  # cleaner public URLs

AWS_STORAGE_BUCKET_NAME_STATIC = "quelo-static"
AWS_STORAGE_BUCKET_NAME_MEDIA = "quelo-media"

# settings.py
# CACHES = {
#     "default": {
#         "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
#         "LOCATION": "unique-quelo-cache",
#     }
# }

# Public, cacheable URLs (no signed querystrings)
AWS_S3_SIGNATURE_VERSION = "s3v4"

# Optional: long cache for static assets
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=31536000, public",
}

# -----------------
DEFAULT_FILE_STORAGE = "quelo_backend.storage_backends.MediaStorage"
MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME_MEDIA}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/media/"

STATICFILES_STORAGE = "quelo_backend.storage_backends.StaticStorage"
STATIC_URL = f"https://{AWS_STORAGE_BUCKET_NAME_STATIC}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/static/"



STATIC_ROOT = None  # not used with S3
# (Optional) Local fallback during dev
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "mediafiles"

# -----
# Templates
# -----------------------------
ROOT_URLCONF = "quelo_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'core.context_processors.global_sidebar_context',
        ],
    },
    },
]




WSGI_APPLICATION = "quelo_backend.wsgi.application"

# -----------------------------
# Database
# -----------------------------
try:
    from functools import lru_cache

    @lru_cache(maxsize=1)
    def get_secret_cached():
        return get_secret()
    secret = get_secret() 
except Exception as e:
    print("⚠️ Could not fetch AWS secret, falling back to local .env:", e)
    secret = {
        "NAME": os.environ.get("DB_NAME", "quelo_local"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "password"),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "3306"),
    }

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        **secret,
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "CONN_MAX_AGE": 300,  # <-- important for rotation (5 min reuse max)
    }
}

# -----------------------------
# Authentication
# -----------------------------
AUTH_USER_MODEL = "core.HospitalUser"
LOGIN_REDIRECT_URL = "/queue/"
LOGOUT_REDIRECT_URL = "/login/"
DEFAULT_USER_PASSWORD = "Quelo@123"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------
# Localization
# -----------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = False  # disabled for IST consistency

# -----------------------------
# Defaults
# -----------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------
# Logging
# -----------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.security.DisallowedHost": {
            "handlers": ["console"],
            "level": "CRITICAL",  # silence DisallowedHost spam
            "propagate": False,
        },
    },
}

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
