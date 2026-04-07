"""
Django settings for AutoParts CRM project.
"""
import os
import sys
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Frozen-exe overrides (PyInstaller) ──────────────────────────────────────
# run_server.py sets APP_BASE_DIR (bundled app files, read-only) and
# APP_DATA_DIR (writable user data: db, media) before importing Django.
if getattr(sys, 'frozen', False):
    _app_base = os.environ.get('APP_BASE_DIR')
    _app_data = os.environ.get('APP_DATA_DIR')
    if _app_base:
        BASE_DIR = Path(_app_base)
    APP_DATA_DIR = Path(_app_data) if _app_data else BASE_DIR
else:
    APP_DATA_DIR = BASE_DIR
# ────────────────────────────────────────────────────────────────────────────

# SECURITY — read from environment in production, fallback for local dev
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-autoparts-crm-key-change-in-production-2024')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Project apps
    'users.apps.UsersConfig',
    'catalog.apps.CatalogConfig',
    'warehouse.apps.WarehouseConfig',
    'orders.apps.OrdersConfig',
    'crm.apps.CrmConfig',
    'reports.apps.ReportsConfig',
    'purchases.apps.PurchasesConfig',
    'portal.apps.PortalConfig',
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

ROOT_URLCONF = 'autoparts.urls'

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
                'portal.context_processors.portal_unread',
            ],
        },
    },
]

WSGI_APPLICATION = 'autoparts.wsgi.application'

# Database — SQLite by default, switchable to PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': APP_DATA_DIR / 'db.sqlite3',
    }
}

# To switch to PostgreSQL, uncomment below and comment the SQLite block:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'autoparts_db',
#         'USER': 'postgres',
#         'PASSWORD': 'your_password',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Internationalization
LANGUAGE_CODE = 'ru'
TIME_ZONE = 'Asia/Almaty'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
# In frozen exe mode static files are pre-collected and bundled inside
# BASE_DIR/staticfiles (populated by build.bat → collectstatic).
# STATICFILES_DIRS must be empty when running from the frozen bundle
# because the 'static' source folder is not separately present.
_frozen = getattr(sys, 'frozen', False)
STATICFILES_DIRS = [] if _frozen else [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedStaticFilesStorage'
    if _frozen
    else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
)

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = APP_DATA_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login / Logout redirects
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# Messages framework
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}
