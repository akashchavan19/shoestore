"""
onistuka/celery.py

Celery application setup.
Celery handles background tasks so views return fast:
- Order confirmation emails
- Payment notification emails
- Any other slow operations

Usage:
  Start worker: celery -A onistuka worker -l info
  Start beat:   celery -A onistuka beat -l info  (for scheduled tasks)
"""

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onistuka.settings.dev')

app = Celery('onistuka')

# Load config from Django settings, namespace CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py in all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Test task — run with: python manage.py shell -c "from onistuka.celery import debug_task; debug_task.delay()" """
    print(f'Request: {self.request!r}')
