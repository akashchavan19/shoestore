# Load Celery app when Django starts — only if Celery is installed
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery not installed — app runs without async tasks
    # Install celery and redis in production: pip install celery redis
    pass
