from django.test import TestCase
from .models import User, UserRole
from .permissions import get_user_permissions, Permissions

class RBACTest(TestCase):
    def test_auditor_permissions(self):
        user = User.objects.create_user(username="auditor", password="pw", role=UserRole.AUDITOR)
        perms = get_user_permissions(user)
        self.assertIn(Permissions.LEDGER_VIEW_EXPENSE, perms)
        self.assertNotIn(Permissions.LEDGER_CREATE_EXPENSE, perms)
        
    def test_homeowner_permissions(self):
        user = User.objects.create_user(username="owner", password="pw", role=UserRole.HOMEOWNER)
        perms = get_user_permissions(user)
        # Check against what we defined in permissions.py (list might change, so checking membership is safet)
        self.assertIn(Permissions.GOVERNANCE_VIEW_DOCS, perms)
        self.assertNotIn(Permissions.LEDGER_VIEW_EXPENSE, perms)

    def test_admin_permissions(self):
        user = User.objects.create_user(username="admin", password="pw", role=UserRole.ADMIN)
        perms = get_user_permissions(user)
        self.assertIn(Permissions.LEDGER_CREATE_EXPENSE, perms)
        
    def test_staff_permissions(self):
        user = User.objects.create_user(username="staff", password="pw", role=UserRole.STAFF)
        perms = get_user_permissions(user)
        self.assertIn(Permissions.LEDGER_CREATE_EXPENSE, perms)
        self.assertNotIn(Permissions.LEDGER_APPROVE_EXPENSE, perms)
