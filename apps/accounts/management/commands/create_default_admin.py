from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Kreira default admin korisnika'

    def handle(self, *args, **kwargs):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                password='Admin1234!',
                email='admin@rezervisi.ba',
                phone=None,
                phone_verified=True,
            )
            self.stdout.write(self.style.SUCCESS('Admin kreiran: admin / Admin1234!'))
        else:
            self.stdout.write('Admin već postoji.')