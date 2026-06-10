"""
Development settings for Onistuka.
Use: DJANGO_SETTINGS_MODULE=onistuka.settings.dev
"""

from .base import *  # noqa: F401, F403

DEBUG         = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Dev-only apps
INSTALLED_APPS += ['django_extensions']  # noqa: F405

# SQLite for local dev
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
    }
}

# In dev — use local memory cache (no Redis needed)
# Swap to Redis by setting REDIS_URL in .env and uncommenting below
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'onistuka-dev',
    }
}

# To use Redis locally (optional):
# REDIS_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/1')  # noqa: F405
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': REDIS_URL,
#         'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
#         'KEY_PREFIX': 'onistuka_dev',
#     }
# }

EMAIL_BACKEND      = 'django.core.mail.backends.console.EmailBackend'
CORS_ALLOW_ALL_ORIGINS = True
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Show slow queries in terminal — set to DEBUG to see all SQL
LOGGING['loggers']['django.db.backends']['level'] = 'WARNING'  # noqa: F405
