"""
config/settings.py — Kompletne Django postavke za RezervišiBiH
"""
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='django-insecure-PROMIJENI-OVO-U-PRODUKCIJI')
DEBUG = env('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# ── Aplikacije ────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    'django_celery_beat',
    # Lokalne aplikacije
    'apps.accounts.apps.AccountsConfig',
    'apps.businesses.apps.BusinessesConfig',
    'apps.services.apps.ServicesConfig',
    'apps.availability.apps.AvailabilityConfig',
    'apps.appointments.apps.AppointmentsConfig',
    'apps.notifications.apps.NotificationsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

WSGI_APPLICATION = 'config.wsgi.application'

# ── Baza podataka ─────────────────────────────────────────────
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')
}

# ── Autentifikacija ───────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = '/prijava/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internacionalizacija ──────────────────────────────────────
LANGUAGE_CODE = 'bs'
TIME_ZONE = 'Europe/Sarajevo'
USE_I18N = True
USE_TZ = True

# ── Static i Media fajlovi ────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Crispy Forms ──────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ── Session ───────────────────────────────────────────────────
SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = True

# ── Celery ────────────────────────────────────────────────────
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Sarajevo'

# ── SMS / Messaging provideri ─────────────────────────────────
INFOBIP_API_KEY   = env('INFOBIP_API_KEY', default='')
INFOBIP_BASE_URL  = env('INFOBIP_BASE_URL', default='')
VIBER_SENDER_NAME = env('VIBER_SENDER_NAME', default='RezervišiBiH')

WHATSAPP_TOKEN    = env('WHATSAPP_TOKEN', default='')
WHATSAPP_PHONE_ID = env('WHATSAPP_PHONE_ID', default='')

TWILIO_ACCOUNT_SID  = env('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN   = env('TWILIO_AUTH_TOKEN', default='')
TWILIO_FROM_NUMBER  = env('TWILIO_FROM_NUMBER', default='')

# ── Email ─────────────────────────────────────────────────────
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST          = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT          = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = env('DEFAULT_FROM_EMAIL', default='noreply@rezervisi.ba')

# ── Logging (samo konzola, bez file handlera) ─────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'apps.notifications': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}