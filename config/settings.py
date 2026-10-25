import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ["SECRET_KEY"]
ACCESS_CODE = os.environ["ACCESS_CODE"]
if not re.fullmatch(r"[0-9]{6}", ACCESS_CODE):
    raise ValueError("ACCESS_CODE must be exactly six ASCII digits.")
DEBUG = os.environ.get("DEBUG") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8098").rstrip("/")
if not DEBUG and not PUBLIC_BASE_URL.startswith("https://"):
    raise ValueError("Production requires an HTTPS PUBLIC_BASE_URL.")
CSRF_TRUSTED_ORIGINS = [PUBLIC_BASE_URL]
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "qrapp",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "qrapp.middleware.Headers",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    }
]
if os.environ.get("LOCAL_TEST") == "1":
    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.environ.get("LOCAL_DB", ":memory:")}
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "qrstudio"),
            "USER": os.environ.get("POSTGRES_USER", "qrstudio"),
            "PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "HOST": os.environ.get("DB_HOST", "db"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_AGE = 86400
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Strict"
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"
TRUST_PROXY = os.environ.get("TRUST_PROXY") == "1"
if TRUST_PROXY:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
X_FRAME_OPTIONS = "DENY"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
if DEBUG:
    STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SOURCE_REVISION = os.environ.get("SOURCE_REVISION", "development")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "loggers": {
        "django.request": {"handlers": ["null"], "propagate": False},
        "django.security": {"handlers": ["null"], "propagate": False},
    },
}
