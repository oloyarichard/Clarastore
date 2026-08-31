"""
Django settings for ecommerce_uganda project.
"""
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=lambda v: [s.strip() for s in v.split(',')])

# Django's own default here (2.5MB) is smaller than a typical phone
# camera photo — raised to match Nginx's client_max_body_size, since
# fixing one without the other just trades a 413 from Nginx for a
# less obvious rejection from Django itself.
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'corsheaders',
]

LOCAL_APPS = [
    'accounts',
    'catalog',
    'orders',
    'wallets',
    'webapp',
    'negotiations',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.AdminLoginRateLimitMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ecommerce_uganda.urls'

TEMPLATES = [
    {
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
    },
]

WSGI_APPLICATION = 'ecommerce_uganda.wsgi.application'
ASGI_APPLICATION = 'ecommerce_uganda.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='ecommerce_uganda'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Kampala'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'accounts.authentication.CookieJWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_RATES': {
        # Deliberately tight — login guards against credential stuffing,
        # negotiation guards the one shared Ollama instance from being
        # tied up indefinitely by a single scripted attacker, topup
        # guards against using this as a harassment vector against an
        # arbitrary third party's phone (the endpoint never verified
        # the number belongs to the requester, so without a limit here
        # nothing stopped repeated real payment prompts to a stranger).
        'login': '5/min',
        'negotiation': '15/min',
        'topup': '5/min',
        'registration': '5/min',
        'password_reset': '5/min',
        'checkout': '10/min',
        'order_status': '30/min',
        'cart': '30/min',
        'webhook': '30/min',
    },
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    'auto-flag-overdue-orders': {
        'task': 'orders.tasks.auto_flag_overdue_orders',
        'schedule': timedelta(minutes=15),
    },
    'expire-stale-negotiation-agreements': {
        'task': 'negotiations.tasks.expire_stale_agreements',
        'schedule': timedelta(minutes=15),
    },
    'expire-inactive-carts': {
        'task': 'negotiations.tasks.expire_inactive_carts',
        'schedule': timedelta(hours=1),
    },
    'refresh-market-snapshots': {
        'task': 'negotiations.tasks.refresh_market_snapshots',
        'schedule': timedelta(hours=1),
    },
}

# MTN MoMo Configuration
MOMO_BASE_URL = config('MOMO_BASE_URL', default='https://sandbox.momodeveloper.mtn.com')
MOMO_SUBSCRIPTION_KEY = config('MOMO_SUBSCRIPTION_KEY', default='')
MOMO_API_USER = config('MOMO_API_USER', default='')
MOMO_API_KEY = config('MOMO_API_KEY', default='')
MOMO_TARGET_ENVIRONMENT = config('MOMO_TARGET_ENVIRONMENT', default='sandbox')

# Airtel Money Configuration
AIRTEL_BASE_URL = config('AIRTEL_BASE_URL', default='https://openapiuat.airtel.africa')
AIRTEL_CLIENT_ID = config('AIRTEL_CLIENT_ID', default='')
AIRTEL_CLIENT_SECRET = config('AIRTEL_CLIENT_SECRET', default='')
AIRTEL_COUNTRY = config('AIRTEL_COUNTRY', default='UG')
AIRTEL_CURRENCY = config('AIRTEL_CURRENCY', default='UGX')

# CORS Configuration
# Required for the standalone website (a different origin than this API)
# to call it from the browser, including credentialed requests — the guest
# cart relies on the Django session cookie, which only gets sent
# cross-origin when CORS_ALLOW_CREDENTIALS is on and the origin is
# explicitly allowed (the wildcard '*' is not permitted together with
# credentials by the CORS spec).
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:8099,http://127.0.0.1:8099',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)
CORS_ALLOW_CREDENTIALS = True

# Business Constants
AGENT_MINIMUM_FLOAT = 100000  # UGX
COMMISSION_RATE = 0.10  # 10%

# Negotiation layer — seller_floor must always be at least this much above
# cost_price. Enforced at the model level (Product.clean()/save()), not
# just a UI suggestion — a save attempting to violate this is rejected
# outright. Stored as a fraction (0.10 = 10%), matching COMMISSION_RATE's
# convention above.
MINIMUM_MARGIN_PERCENT = 0.10

# How long an agreed negotiated price stays valid before checkout must
# happen — after this, the agreement expires and the cart item reverts.
NEGOTIATION_AGREEMENT_EXPIRY_HOURS = 24

# Any cart item (negotiated or not) clears after this long with no activity
CART_INACTIVITY_EXPIRY_HOURS = 24

# Configurable weighting for the market signal engine — internal-only for
# now per the agreed priority order (demand/inventory highest, exchange
# rate and seasonal signals present as real fields but held neutral until
# a live external source is actually wired in). Change these numbers to
# retune scoring without touching negotiations/services.py.
MARKET_SIGNAL_WEIGHTS = {
    'demand': 0.40,
    'inventory': 0.25,
    'velocity_bonus_cap': 0.20,
    'exchange_rate': 0.10,
    'seasonal': 0.05,
}

OLLAMA_BASE_URL = config('OLLAMA_BASE_URL', default='http://localhost:11434')
OLLAMA_MODEL = config('OLLAMA_MODEL', default='phi4-mini')

# Free tier, no card required — get a key at https://aistudio.google.com/apikey
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
GEMINI_MODEL = config('GEMINI_MODEL', default='gemini-2.5-flash')

# GosentePay — unified MTN/Airtel collection & disbursement gateway,
# replacing direct MTN MoMo / Airtel Money integration. Get keys from
# the dashboard at https://gosentepay.com/dashboard/ under API Keys.
GOSENTEPAY_BASE_URL = config('GOSENTEPAY_BASE_URL', default='https://api.gosentepay.com/v1')
GOSENTEPAY_API_KEY = config('GOSENTEPAY_API_KEY', default='')
GOSENTEPAY_SECRET_KEY = config('GOSENTEPAY_SECRET_KEY', default='')

# Used to build the absolute callback URL GosentePay POSTs transaction
# results to — must be your real, publicly-reachable domain in
# production (a webhook can't reach localhost).
SITE_URL = config('SITE_URL', default='http://localhost:8000')

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@clarastock.com')

# Without these, Django silently falls back to its own default
# (localhost:25, no authentication) — which fails on almost any real
# server, since most providers block outbound port 25 by default
# specifically to prevent spam abuse. Every notification built this
# project (order confirmations, refunds, welcome emails, commission
# and wallet-adjustment notices) is fully tested against Django's
# in-memory test backend, but sends nothing for real until these are
# set to genuine SMTP credentials in .env.
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=465, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=True, cast=bool)

DELIVERY_CONFIRMATION_HOURS = 24
