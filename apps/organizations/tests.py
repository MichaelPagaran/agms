from django.test import TestCase
from uuid import uuid4
from apps.organizations.models import Organization, OrganizationType
from apps.identity.models import User, UserRole
from apps.registry.models import Unit, UnitCategory
from apps.registry.services import list_units, create_unit
from apps.registry.dtos import UnitIn
from apps.identity.permissions import Permissions

class MultiTenancyTest(TestCase):
    def setUp(self):
        # Create Org A
        self.org_a = Organization.objects.create(name="Org A", org_type="SUBDIVISION")
        self.staff_a = User.objects.create_user(username="staff_a", role=UserRole.STAFF, org_id=self.org_a.id)
        
        # Create Org B
        self.org_b = Organization.objects.create(name="Org B", org_type="CONDOMINIUM")
        self.staff_b = User.objects.create_user(username="staff_b", role=UserRole.STAFF, org_id=self.org_b.id)
        
        # Platform Admin (Super)
        self.admin = User.objects.create_user(username="admin_p", role=UserRole.ADMIN) 
        # Assume Admin permissions are set correctly via RBAC or is_superuser

    def test_unit_creation_isolation(self):
        # Staff A creates unit in Org A
        payload = UnitIn(
            section_identifier="B1", unit_identifier="L1", location_name="St", category="UNIT",
            resident_name="Res A"
        )
        unit_a = create_unit(self.org_a.id, payload)
        
        # Staff B creates unit in Org B
        payload_b = UnitIn(
            section_identifier="F1", unit_identifier="U1", location_name="Twr", category="UNIT",
             resident_name="Res B"
        )
        unit_b = create_unit(self.org_b.id, payload_b)
        
        self.assertEqual(unit_a.org_id, self.org_a.id)
        self.assertEqual(unit_b.org_id, self.org_b.id)

    def test_list_units_isolation(self):
        # Setup data
        payload = UnitIn(section_identifier="1", unit_identifier="1", location_name="L", category="UNIT")
        create_unit(self.org_a.id, payload) # Unit in A
        create_unit(self.org_b.id, payload) # Unit in B
        
        # Staff A should see 1 unit
        units_a = list_units(self.org_a.id, self.staff_a.id, view_all=True)
        self.assertEqual(len(units_a), 1)
        self.assertEqual(units_a[0].org_id, self.org_a.id)
        
        # Staff B should see 1 unit
        units_b = list_units(self.org_b.id, self.staff_b.id, view_all=True)
        self.assertEqual(len(units_b), 1)
        self.assertEqual(units_b[0].org_id, self.org_b.id)

    def test_create_organization_permission(self):
        # Staff cannot create org
        response = self.client.post(
            "/api/organizations/",
            {"name": "New Org", "org_type": "SUBDIVISION", "settings": {}},
            content_type="application/json",
            **{'HTTP_X_USER_ID': str(self.staff_a.id)} # Mocking auth if needed, but we rely on simple login usually.
        )
        # Wait, for APIClient in Ninja/Django, we need to handle Auth.
        # My tests use API functions usually or client.force_login?
        # Let's use simple logic:
        # If I use `self.client.force_login(self.staff_a)`, I can test endpoint.
        self.client.force_login(self.staff_a)
        response = self.client.post(
            "/api/organizations/",
            {"name": "New Org", "org_type": "SUBDIVISION", "settings": {}},
             content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

        # Admin CAN create org
        self.client.force_login(self.admin)
        response = self.client.post(
            "/api/organizations/",
            {"name": "New Org", "org_type": "SUBDIVISION", "settings": {}},
             content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Organization.objects.count(), 3)

