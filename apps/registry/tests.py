from django.test import TestCase
from django.db import IntegrityError
from apps.identity.models import User, UserRole
from .models import Unit, UnitCategory
from .services import create_unit, list_units, soft_delete_unit
from .dtos import UnitIn
import uuid

class RegistryTest(TestCase):
    def setUp(self):
        self.org_id = uuid.uuid4()
        self.staff = User.objects.create_user(username="staff", role=UserRole.STAFF, org_id=self.org_id)
        self.admin = User.objects.create_user(username="admin", role=UserRole.ADMIN, org_id=self.org_id)
        self.homeowner = User.objects.create_user(username="owner", role=UserRole.HOMEOWNER, org_id=self.org_id)
        self.auditor = User.objects.create_user(username="auditor", role=UserRole.AUDITOR, org_id=self.org_id)

    def test_create_unit_success(self):
        payload = UnitIn(
            section_identifier="Block 1",
            unit_identifier="Lot 2",
            location_name="Main St",
            category="UNIT",
            resident_name="John Doe"
        )
        unit = create_unit(self.org_id, payload)
        self.assertEqual(unit.resident_name, "John Doe")
        self.assertEqual(unit.full_label, "Main St Block 1 Lot 2")

    def test_uniqueness_constraint(self):
        payload = UnitIn(
            section_identifier="Block 1",
            unit_identifier="Lot 2",
            location_name="Main St",
            category="UNIT"
        )
        create_unit(self.org_id, payload)
        
        # Duplicate should fail
        with self.assertRaises(IntegrityError):
            create_unit(self.org_id, payload)

    def test_soft_delete(self):
        payload = UnitIn(
            section_identifier="B2", unit_identifier="L2", location_name="X", category="UNIT"
        )
        unit = create_unit(self.org_id, payload)
        
        # Soft Delete
        success = soft_delete_unit(unit.id)
        self.assertTrue(success)
        
        # Verify inactive
        unit.refresh_from_db()
        self.assertFalse(unit.is_active)
        
        # Service should not list it
        units = list_units(self.org_id, self.staff.id, view_all=True)
        self.assertNotIn(unit, units)

    def test_list_access_logic(self):
        # Create unit owned by homeowner
        payload = UnitIn(
            section_identifier="B3", unit_identifier="L3", location_name="Y", category="UNIT",
            owner_id=self.homeowner.id
        )
        unit1 = create_unit(self.org_id, payload)
        
        # Create unowned unit
        payload2 = UnitIn(
            section_identifier="B4", unit_identifier="L4", location_name="Y", category="INFRASTRUCTURE"
        )
        unit2 = create_unit(self.org_id, payload2)
        
        # Homeowner sees only own
        ho_units = list_units(self.org_id, self.homeowner.id, view_all=False)
        self.assertIn(unit1, ho_units)
        self.assertNotIn(unit2, ho_units)
        
        # Staff (view_all=True) sees both
        staff_units = list_units(self.org_id, self.staff.id, view_all=True)
        self.assertIn(unit1, staff_units)
        self.assertIn(unit2, staff_units)
