import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onistuka.settings.prod')
django.setup()

from django.contrib.auth.models import User

# Delete existing and recreate fresh
User.objects.filter(username='admin').delete()

User.objects.create_superuser(
    username='admin',
    email='akashshivachavan99@gmail.com',
    password='Akash@Admin2026'
)
print('Superuser created fresh')