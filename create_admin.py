import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onistuka.settings.prod')
django.setup()

from django.contrib.auth.models import User

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='akashshivachavan99@gmail.com',
        password='Akash@Admin2026'
    )
    print('Superuser created successfully')
else:
    print('Superuser already exists')