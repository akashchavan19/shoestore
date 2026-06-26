"""
Production settings for Onistuka.
Use: DJANGO_SETTINGS_MODULE=onistuka.settings.prod
All secrets MUST come from environment variables — never hardcoded.
"""

import logging
from .base import *  # noqa: F401, F403

logger = logging.getLogger('onistuka')

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG         = False
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')  # noqa: F405
# e.g. ALLOWED_HOSTS=onistuka.com,www.onistuka.com

# ---------------------------------------------------------------------------
# Database — PostgreSQL (mandatory in prod, SQLite cannot handle load)
# ---------------------------------------------------------------------------
DATABASES = {
    'default': env.db('DATABASE_URL')  # noqa: F405
    # e.g. DATABASE_URL=postgres://user:pass@host:5432/onistuka_db
}
# Keep DB connections alive for 60s — reduces connection overhead
DATABASES['default']['CONN_MAX_AGE'] = 60
# Ensure atomic requests — wraps each request in a transaction
DATABASES['default']['ATOMIC_REQUESTS'] = True

# ---------------------------------------------------------------------------
# Security Headers — all required for production
# ---------------------------------------------------------------------------
SECURE_BROWSER_XSS_FILTER      = True
SECURE_CONTENT_TYPE_NOSNIFF    = True
X_FRAME_OPTIONS                = 'DENY'

# HSTS — tells browsers to always use HTTPS (1 year)
SECURE_HSTS_SECONDS            = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD            = True

# Force all traffic to HTTPS
SECURE_SSL_REDIRECT            = True

# Cookies only sent over HTTPS
SESSION_COOKIE_SECURE          = True
SESSION_COOKIE_HTTPONLY        = True
SESSION_COOKIE_SAMESITE        = 'Lax'
SESSION_COOKIE_AGE             = 60 * 60 * 24 * 14  # 2 weeks

CSRF_COOKIE_SECURE             = True
CSRF_COOKIE_HTTPONLY           = True
CSRF_COOKIE_SAMESITE           = 'Lax'

# ---------------------------------------------------------------------------
# Redis — cache + sessions + Celery broker
# ---------------------------------------------------------------------------
  # noqa: F405
# Redis cache — graceful fallback to database if Redis not available
REDIS_URL = env('REDIS_URL', default='')  # noqa: F405

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND':  'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS':           'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT':         5,
                'IGNORE_EXCEPTIONS':      True,
                'COMPRESSOR':             'django_redis.compressors.zlib.ZlibCompressor',
            },
            'KEY_PREFIX': 'onistuka',
            'TIMEOUT':    300,
        }
    }
    SESSION_ENGINE      = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
    CELERY_BROKER_URL     = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
else:
    # No Redis — use database cache (works on free Render plan)
    CACHES = {
        'default': {
            'BACKEND':  'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'cache_table',
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'
# ---------------------------------------------------------------------------
# Email — SMTP (e.g. SendGrid, Mailgun, AWS SES)
# ---------------------------------------------------------------------------
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = env('EMAIL_HOST')                          # noqa: F405
EMAIL_PORT          = env.int('EMAIL_PORT', default=587)         # noqa: F405
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = env('EMAIL_HOST_USER')                     # noqa: F405
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')                 # noqa: F405
DEFAULT_FROM_EMAIL  = env('DEFAULT_FROM_EMAIL',                  # noqa: F405
                          default='noreply@onistuka.com')

# ---------------------------------------------------------------------------
# Static files — WhiteNoise serves compressed files with long cache headers
# ---------------------------------------------------------------------------
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ---------------------------------------------------------------------------
# CORS — locked to your domain only
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS   = env.list('CORS_ALLOWED_ORIGINS')  # noqa: F405
# e.g. CORS_ALLOWED_ORIGINS=https://onistuka.com,https://www.onistuka.com

# ---------------------------------------------------------------------------
# Logging — structured logs to console + rotating file
# Render/Railway/Heroku collect stdout automatically
# ---------------------------------------------------------------------------
LOGGING['handlers']['file'] = {  # noqa: F405
    'class':       'logging.handlers.RotatingFileHandler',
    'filename':    BASE_DIR / 'logs' / 'django.log',  # noqa: F405
    'maxBytes':    1024 * 1024 * 5,   # 5 MB per file
    'backupCount': 5,
    'formatter':   'verbose',
}
LOGGING['root']['handlers']           = ['console', 'file']  # noqa: F405
LOGGING['loggers']['django']['level'] = 'WARNING'             # noqa: F405
# Don't log every SQL query in prod
LOGGING['loggers']['django.db.backends']['level'] = 'ERROR'  # noqa: F405
