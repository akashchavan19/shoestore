"""
WSGI config for Onistuka.
Gunicorn uses this file to serve the application.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onistuka.settings.prod')
application = get_wsgi_application()
