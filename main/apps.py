from django.apps import AppConfig
from django.db.models.signals import post_migrate
from decouple import config

class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        # Import User here to ensure apps are loaded
        from django.contrib.auth.models import User
        def create_default_superuser(sender, **kwargs):
            # Fetch superuser credentials from .env or fallback to default
            username = config('SUPERUSER_USERNAME', default='admin')
            password = config('SUPERUSER_PASSWORD', default='admin')

            # Check if the superuser already exists
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username=username, password=password)
                print(f"Default superuser created: {username} / {password}")
            else:
                print(f"Superuser {username} already exists.")
        post_migrate.connect(create_default_superuser, sender=self)