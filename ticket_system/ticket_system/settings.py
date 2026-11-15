"""
Django settings for ticket_system.

Every secret and environment-specific value comes from environment variables,
loaded from a `.env` file next to manage.py. Copy `.env.example` to `.env`.
Never commit `.env`.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    return env(key, str(default)).lower() in ("1", "true", "yes", "on")


def env_list(key, default=""):
    return [v.strip() for v in env(key, default).split(",") if v.strip()]


DEBUG = env_bool("DEBUG", False)
SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-change-me"
    else:
        raise RuntimeError("SECRET_KEY is not set. Add it to your .env file.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
# Render sets this automatically to e.g. bustick-api.onrender.com
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Public URLs (used for payment redirects and emails)
FRONTEND_URL = env("FRONTEND_URL", "http://localhost:3000").rstrip("/")
BACKEND_URL = env("BACKEND_URL", f"https://{RENDER_EXTERNAL_HOSTNAME}" if RENDER_EXTERNAL_HOSTNAME else "http://127.0.0.1:8000").rstrip("/")

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", FRONTEND_URL)
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", FRONTEND_URL)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "corsheaders",
    "rest_framework",
    "booking",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ticket_system.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ticket_system.wsgi.application"

# Render (and most hosts) provide DATABASE_URL for Postgres. Without it, SQLite is used locally.
if env("DATABASE_URL"):
    import dj_database_url
    DATABASES = {"default": dj_database_url.parse(env("DATABASE_URL"), conn_max_age=600, conn_health_checks=True)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", "Asia/Dhaka")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    # The public booking API needs no login; the admin uses Django sessions.
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": env("API_RATE_LIMIT", "120/min")},
}

# ---- Booking rules ----
SEAT_HOLD_MINUTES = int(env("SEAT_HOLD_MINUTES", "10"))
MAX_SEATS_PER_BOOKING = int(env("MAX_SEATS_PER_BOOKING", "4"))
RETURN_CUTOFF_HOURS = int(env("RETURN_CUTOFF_HOURS", "12"))
CURRENCY = env("CURRENCY", "BDT")
BRAND_NAME = env("BRAND_NAME", "BusTick")
# Where messages from the Help page contact form are sent
SUPPORT_EMAIL = env("SUPPORT_EMAIL", "arabid8427@gmail.com")

# ---- Payments ----
# PAYMENT_PROVIDER: sslcommerz | stripe | demo
PAYMENT_PROVIDER = env("PAYMENT_PROVIDER", "demo" if DEBUG else "sslcommerz").lower()

SSLCOMMERZ_STORE_ID = env("SSLCOMMERZ_STORE_ID", "")
SSLCOMMERZ_STORE_PASSWORD = env("SSLCOMMERZ_STORE_PASSWORD", "")
SSLCOMMERZ_SANDBOX = env_bool("SSLCOMMERZ_SANDBOX", True)

STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", "")

# Set ALLOW_DEMO_PAYMENTS=True only for a public portfolio/demo site where no real money is involved.
ALLOW_DEMO_PAYMENTS = env_bool("ALLOW_DEMO_PAYMENTS", False)
if PAYMENT_PROVIDER == "demo" and not (DEBUG or ALLOW_DEMO_PAYMENTS):
    raise RuntimeError("PAYMENT_PROVIDER=demo needs DEBUG=True or ALLOW_DEMO_PAYMENTS=True.")

# ---- Email ----
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@example.com")
# For hosts that block SMTP (e.g. Render free tier): EMAIL_BACKEND=booking.email_backends.BrevoEmailBackend
BREVO_API_KEY = env("BREVO_API_KEY", "")

# ---- Production hardening ----
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_CONTENT_TYPE_NOSNIFF = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"booking": {"handlers": ["console"], "level": "INFO"}},
}
