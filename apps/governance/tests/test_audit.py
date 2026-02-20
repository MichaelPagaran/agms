"""
Tests for the Audit Logging system.

Covers:
1. audit_service.log_action() — creates an AuditLog with correct fields
2. GET /governance/audit-logs — list endpoint with filters, auth requirement
3. GET /governance/audit-logs/{id} — detail endpoint
4. Wiring smoke test — creating an expense via the API creates an AuditLog
"""
import json
from uuid import uuid4
from datetime import date

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from apps.organizations.models import Organization, OrganizationType
from apps.identity.models import UserRole
from apps.governance.models import AuditLog
from apps.governance.audit_service import log_action, AuditAction
from apps.ledger.models import TransactionCategory, TransactionType


User = get_user_model()


def make_org():
    """Create a test Organization."""
    return Organization.objects.create(
        name=f"Test HOA {uuid4().hex[:6]}",
        org_type=OrganizationType.SUBDIVISION,
    )


def make_user(org, role=UserRole.ADMIN, username=None):
    """Create a test User in the given org."""
    username = username or f"user_{uuid4().hex[:8]}"
    return User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="testpass123",
        org_id=org,
        role=role,
    )


class AuditServiceTest(TestCase):
    """Test the log_action() helper directly."""

    def setUp(self):
        self.org = make_org()
        self.user = make_user(self.org)
        self.target_id = uuid4()

    def test_log_action_creates_audit_log(self):
        """log_action() should create an AuditLog with correct fields."""
        log = log_action(
            org_id=self.org.id,
            action=AuditAction.CREATE_INCOME,
            target_type="Transaction",
            target_id=self.target_id,
            target_label="Income ₱1000 – Dues",
            performed_by=self.user,
            context={"amount": "1000.00"},
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.action, AuditAction.CREATE_INCOME)
        self.assertEqual(log.target_type, "Transaction")
        self.assertEqual(log.target_id, self.target_id)
        self.assertEqual(log.org_id, self.org.id)
        self.assertEqual(log.performed_by, self.user)
        self.assertEqual(log.context["amount"], "1000.00")

    def test_log_action_never_raises_on_bad_input(self):
        """log_action() should silently return None on failure, never raise."""
        result = log_action(
            org_id=self.org.id,
            action=AuditAction.DELETE_UNIT,
            target_type="Unit",
            target_id=self.target_id,
            performed_by=None,  # null FK – allowed by model
        )
        # Should not raise — returns None or a valid log
        self.assertTrue(result is None or hasattr(result, "id"))

    def test_log_action_with_no_context(self):
        """log_action() should default context to empty dict."""
        log = log_action(
            org_id=self.org.id,
            action=AuditAction.VERIFY_TRANSACTION,
            target_type="Transaction",
            target_id=self.target_id,
            performed_by=self.user,
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.context, {})


class AuditLogAPITest(TestCase):
    """Test GET /governance/audit-logs endpoints."""

    def setUp(self):
        self.client = Client()
        self.org = make_org()
        self.other_org = make_org()

        # Admin — has LEDGER_VIEW_REPORT permission
        self.admin = make_user(self.org, role=UserRole.ADMIN, username="audit_admin")
        # Homeowner — does NOT have LEDGER_VIEW_REPORT
        self.homeowner = make_user(self.org, role=UserRole.HOMEOWNER, username="audit_homeowner")

        self.target_id = uuid4()

        # Seed audit logs for our org
        self.log1 = AuditLog.objects.create(
            org_id=self.org.id,
            action=AuditAction.CREATE_INCOME,
            target_type="Transaction",
            target_id=self.target_id,
            target_label="Income ₱500",
            performed_by=self.admin,
        )
        self.log2 = AuditLog.objects.create(
            org_id=self.org.id,
            action=AuditAction.DELETE_UNIT,
            target_type="Unit",
            target_id=self.target_id,
            target_label="Block 1 Lot 5",
            performed_by=self.admin,
        )
        # Log from a different org — should NOT be visible
        AuditLog.objects.create(
            org_id=self.other_org.id,
            action=AuditAction.CREATE_EXPENSE,
            target_type="Transaction",
            target_id=self.target_id,
            performed_by=self.admin,
        )

    def test_list_audit_logs_requires_auth(self):
        """Unauthenticated requests should get 401."""
        response = self.client.get("/api/governance/audit-logs")
        self.assertEqual(response.status_code, 401)

    def test_homeowner_cannot_list_audit_logs(self):
        """Homeowners don't have LEDGER_VIEW_REPORT – should get 403."""
        self.client.force_login(self.homeowner)
        response = self.client.get("/api/governance/audit-logs")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_audit_logs(self):
        """Admins should see audit logs for their own org only."""
        self.client.force_login(self.admin)
        response = self.client.get("/api/governance/audit-logs")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        ids = [d["id"] for d in data]
        self.assertIn(str(self.log1.id), ids)
        self.assertIn(str(self.log2.id), ids)
        # Other-org log must not appear
        self.assertEqual(len(data), 2)

    def test_filter_by_action(self):
        """Filtering by action should narrow results."""
        self.client.force_login(self.admin)
        response = self.client.get(
            f"/api/governance/audit-logs?action={AuditAction.CREATE_INCOME}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["action"], AuditAction.CREATE_INCOME)

    def test_filter_by_target_type(self):
        """Filtering by target_type should narrow results."""
        self.client.force_login(self.admin)
        response = self.client.get("/api/governance/audit-logs?target_type=Unit")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["action"], AuditAction.DELETE_UNIT)

    def test_audit_log_response_has_performed_by_name(self):
        """Response should include the performed_by_name field."""
        self.client.force_login(self.admin)
        response = self.client.get("/api/governance/audit-logs")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("performed_by_name", data[0])

    def test_get_audit_log_detail(self):
        """GET /audit-logs/{id} should return a single log."""
        self.client.force_login(self.admin)
        response = self.client.get(f"/api/governance/audit-logs/{self.log1.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], str(self.log1.id))
        self.assertEqual(data["action"], AuditAction.CREATE_INCOME)

    def test_get_audit_log_wrong_org_returns_404(self):
        """Cannot access audit log from a different org."""
        self.client.force_login(self.admin)
        other_log = AuditLog.objects.create(
            org_id=self.other_org.id,
            action=AuditAction.DELETE_ASSET,
            target_type="Asset",
            target_id=uuid4(),
            performed_by=self.admin,
        )
        response = self.client.get(f"/api/governance/audit-logs/{other_log.id}")
        self.assertEqual(response.status_code, 404)


class AuditWiringTest(TestCase):
    """Smoke tests: verify audit logs are created via real API calls."""

    def setUp(self):
        self.client = Client()
        self.org = make_org()
        self.admin = make_user(self.org, role=UserRole.ADMIN, username="wire_admin")
        TransactionCategory.objects.create(
            org_id=self.org.id,
            name="Maintenance",
            transaction_type=TransactionType.EXPENSE,
        )

    def test_create_expense_creates_audit_log(self):
        """Creating an expense via the API should create a CREATE_EXPENSE audit log."""
        self.client.force_login(self.admin)

        before_count = AuditLog.objects.filter(
            org_id=self.org.id, action=AuditAction.CREATE_EXPENSE
        ).count()

        payload = {
            "category": "Maintenance",
            "amount": "250.00",
            "description": "Generator fuel",
            "transaction_date": str(date.today()),
        }
        response = self.client.post(
            "/api/ledger/transactions/expense",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        after_count = AuditLog.objects.filter(
            org_id=self.org.id, action=AuditAction.CREATE_EXPENSE
        ).count()
        self.assertEqual(after_count, before_count + 1)

        log = AuditLog.objects.filter(
            org_id=self.org.id, action=AuditAction.CREATE_EXPENSE
        ).latest("performed_at")
        self.assertEqual(log.target_type, "Transaction")
        self.assertEqual(log.performed_by, self.admin)
