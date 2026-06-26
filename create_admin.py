import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onistuka.settings.prod')
django.setup()

from django.contrib.auth.models import User

# Force delete and recreate
User.objects.filter(username='admin').delete()
User.objects.filter(is_superuser=True).delete()

user = User.objects.create_superuser(
    username='admin',
    email='akashshivachavan99@gmail.com',
    password='Admin1234'
)
print(f'Superuser created: {user.username}')