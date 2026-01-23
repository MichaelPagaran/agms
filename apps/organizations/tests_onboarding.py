from django.test import TestCase, Client
from apps.organizations.models import Organization
from apps.identity.models import User, UserRole
import json

class OnboardingTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_onboard_organization_flow(self):
        """
        Verify that we can onboard a new organization along with its admin user.
        """
        payload = {
            "organization": {
                "name": "Sunnyvale Heights",
                "org_type": "SUBDIVISION",
                "settings": {"test": True}
            },
            "admin_user": {
                "username": "sunny_admin",
                "email": "admin@sunnyvale.com",
                "password": "StrongPassword123!",
                "first_name": "Sunny",
                "last_name": "Admin",
                "role": "ADMIN" # This should be enforced by backend even if I send something else, but let's send valid
            }
        }
        
        response = self.client.post(
            "/api/organizations/onboard",
            data=json.dumps(payload),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify Response Structure
        self.assertIn("organization", data)
        self.assertIn("admin_user", data)
        
        org_id = data["organization"]["id"]
        user_id = data["admin_user"]["id"]
        
        # Verify Database State
        self.assertTrue(Organization.objects.filter(id=org_id).exists())
        self.assertTrue(User.objects.filter(id=user_id).exists())
        
        user = User.objects.get(id=user_id)
        self.assertEqual(user.role, UserRole.ADMIN)
        self.assertEqual(str(user.org_id), org_id)
        self.assertTrue(user.check_password("StrongPassword123!"))
        
        return user, org_id

    def test_add_user_to_organization(self):
        """
        Verify that an Admin can add a new user to their organization.
        """
        # First, onboard
        admin_user, org_id = self.test_onboard_organization_flow()
        
        # Login as Admin
        self.client.force_login(admin_user)
        
        # Add a Staff member
        staff_payload = {
            "username": "staff_member",
            "email": "staff@sunnyvale.com",
            "password": "StaffPassword123!",
            "first_name": "Staff",
            "last_name": "Member",
            "role": "STAFF"
        }
        
        response = self.client.post(
            "/api/identity/users",
            data=json.dumps(staff_payload),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["role"], "STAFF")
        self.assertEqual(str(data["org_id"]), org_id)
        
        # Verify DB
        self.assertTrue(User.objects.filter(username="staff_member").exists())

    def test_add_user_forbidden_for_non_admin(self):
        """
        Verify that a non-admin user cannot add users.
        """
        # First, onboard
        admin_user, org_id = self.test_onboard_organization_flow()
        
        # Create a Staff user (manually or via API)
        staff_user = User.objects.create_user(
            username="staff_test",
            email="staff_test@test.com",
            password="pass",
            role=UserRole.STAFF,
            org_id=org_id
        )
        
        # Login as Staff
        self.client.force_login(staff_user)
        
        # Attempt to add another user
        payload = {
            "username": "intruder",
            "email": "intruder@test.com",
            "password": "pass",
            "first_name": "Intruder",
            "last_name": "User",
            "role": "HOMEOWNER"
        }
        
        response = self.client.post(
            "/api/identity/users",
            data=json.dumps(payload),
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 403)
