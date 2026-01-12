from django.core.management.base import BaseCommand
from apps.identity.models import User, UserRole

class Command(BaseCommand):
    help = 'Seeds the database with RBAC test users'

    def handle(self, *args, **options):
        users = [
            {'username': 'admin', 'role': UserRole.ADMIN},
            {'username': 'staff', 'role': UserRole.STAFF},
            {'username': 'auditor', 'role': UserRole.AUDITOR},
            {'username': 'homeowner', 'role': UserRole.HOMEOWNER},
            {'username': 'board', 'role': UserRole.BOARD},
        ]

        for u in users:
            user, created = User.objects.get_or_create(username=u['username'])
            
            # Common setup
            user.role = u['role']
            if u['role'] == UserRole.ADMIN:
                user.is_staff = True
                user.is_superuser = True
            
            if created:
                user.set_password('password')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created user: {u["username"]} (Role: {u["role"]})'))
            else:
                user.save()
                self.stdout.write(self.style.WARNING(f'Updated user: {u["username"]}'))
