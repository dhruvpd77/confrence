import os

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create default super admin user (admin / admin123, or DJANGO_SUPERADMIN_PASSWORD)'

    def handle(self, *args, **options):
        username = 'admin'
        password = os.environ.get('DJANGO_SUPERADMIN_PASSWORD', 'admin123')
        email = 'admin@icraet2026.com'

        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.save()
            self.stdout.write(self.style.WARNING(f'Super admin "{username}" password reset.'))
        else:
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Super admin created: username="{username}" password="{password}"'))
