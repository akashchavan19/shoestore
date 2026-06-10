"""
ASGI config for Onistuka project.
Needed for async support and Channels (WebSockets) later.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onistuka.settings.dev')
application = get_asgi_application()
