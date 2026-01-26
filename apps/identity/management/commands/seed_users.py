from django.core.management.base import BaseCommand
from apps.identity.models import User, UserRole
import uuid

class Command(BaseCommand):
    help = 'Seeds the database with RBAC test users'

    def handle(self, *args, **options):
        # Fake Org ID for testing
        test_org_id = uuid.uuid4()
        
        users = [
            {
                'username': 'admin',
                'role': UserRole.ADMIN,
                'first_name': 'Maria',
                'last_name': 'Santos',
                'phone_number': '09171234567'
            },
            {
                'username': 'staff',
                'role': UserRole.STAFF,
                'first_name': 'Juan',
                'last_name': 'Dela Cruz',
                'phone_number': '09181234567'
            },
            {
                'username': 'auditor',
                'role': UserRole.AUDITOR,
                'first_name': 'Jose',
                'last_name': 'Rizal',
                'phone_number': '09191234567'
            },
            {
                'username': 'homeowner',
                'role': UserRole.HOMEOWNER,
                'first_name': 'Andres',
                'last_name': 'Bonifacio',
                'phone_number': '09201234567'
            },
            {
                'username': 'board',
                'role': UserRole.BOARD,
                'first_name': 'Gabriela',
                'last_name': 'Silang',
                'phone_number': '09211234567'
            },
        ]

        for u in users:
            user, created = User.objects.get_or_create(username=u['username'])
            
            # Common setup
            user.role = u['role']
            user.first_name = u.get('first_name', '')
            user.last_name = u.get('last_name', '')
            user.phone_number = u.get('phone_number', '')
            # Set org_id if not set (or always set for test consistency)
            if not user.org_id:
                user.org_id = test_org_id
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
