"""
Integration tests for ledger API endpoints.
Tests API responses, permissions, and end-to-end flows.
"""
import json
from decimal import Decimal
from datetime import date
from uuid import uuid4
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from apps.ledger.models import (
    Transaction, TransactionCategory, TransactionType, TransactionStatus,
    DiscountConfig, DiscountType, PenaltyPolicy,
)
from apps.identity.models import UserRole


User = get_user_model()


class TransactionAPITest(TestCase):
    """Test transaction API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.org_id = uuid4()
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            org_id=self.org_id,
            role=UserRole.ADMIN,
        )
        
        # Create staff user
        self.staff_user = User.objects.create_user(
            username='staff_test',
            email='staff@test.com',
            password='testpass123',
            org_id=self.org_id,
            role=UserRole.STAFF,
        )
        
        # Create auditor user (view only)
        self.auditor_user = User.objects.create_user(
            username='auditor_test',
            email='auditor@test.com',
            password='testpass123',
            org_id=self.org_id,
            role=UserRole.AUDITOR,
        )
        
        # Create a transaction category
        self.category = TransactionCategory.objects.create(
            org_id=self.org_id,
            name='Monthly Dues',
            transaction_type=TransactionType.INCOME,
        )
        
        # Create a test transaction
        self.transaction = Transaction.objects.create(
            org_id=self.org_id,
            transaction_type=TransactionType.INCOME,
            status=TransactionStatus.DRAFT,
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('1000.00'),
            amount=Decimal('1000.00'),
            category='Monthly Dues',
            transaction_date=date.today(),
        )
    
    def test_list_transactions_requires_auth(self):
        """Test that listing transactions requires authentication."""
        response = self.client.get('/api/ledger/transactions')
        self.assertEqual(response.status_code, 401)
    
    def test_list_transactions_as_staff(self):
        """Test staff can list transactions."""
        self.client.force_login(self.staff_user)
        response = self.client.get('/api/ledger/transactions')
        self.assertEqual(response.status_code, 200)
    
    def test_list_transactions_as_auditor(self):
        """Test auditor can list transactions."""
        self.client.force_login(self.auditor_user)
        response = self.client.get('/api/ledger/transactions')
        self.assertEqual(response.status_code, 200)
    
    def test_get_transaction_detail(self):
        """Test getting transaction details."""
        self.client.force_login(self.staff_user)
        response = self.client.get(f'/api/ledger/transactions/{self.transaction.id}')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['net_amount'], '1000.00')
    
    def test_create_expense_as_staff(self):
        """Test staff can create expenses."""
        self.client.force_login(self.staff_user)
        
        payload = {
            'category': 'Utilities',
            'amount': '500.00',
            'description': 'Electric bill',
            'transaction_date': str(date.today()),
        }
        
        response = self.client.post(
            '/api/ledger/transactions/expense',
            data=json.dumps(payload),
            content_type='application/json',
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['transaction_type'], 'EXPENSE')
        self.assertEqual(data['status'], 'DRAFT')


class ApprovalWorkflowAPITest(TestCase):
    """Test approval workflow API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.org_id = uuid4()
        
        # Create admin user (can approve)
        self.admin_user = User.objects.create_user(
            username='approver',
            email='approver@test.com',
            password='testpass123',
            org_id=self.org_id,
            role=UserRole.ADMIN,
        )
        
        # Create staff user (can create, cannot approve)
        self.staff_user = User.objects.create_user(
            username='creator',
            email='creator@test.com',
            password='testpass123',
            org_id=self.org_id,
            role=UserRole.STAFF,
        )
        
        # Create a draft transaction
        self.transaction = Transaction.objects.create(
            org_id=self.org_id,
            transaction_type=TransactionType.INCOME,
            status=TransactionStatus.DRAFT,
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('1000.00'),
            amount=Decimal('1000.00'),
            category='Monthly Dues',
            transaction_date=date.today(),
        )
    
    def test_submit_transaction_for_approval(self):
        """Test staff can submit transaction for approval."""
        self.client.force_login(self.staff_user)
        
        response = self.client.post(
            f'/api/ledger/transactions/{self.transaction.id}/submit'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'PENDING')
        
        # Verify in database
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.status, TransactionStatus.PENDING)
    
    def test_approve_transaction_as_admin(self):
        """Test admin can approve transactions."""
        # First submit the transaction
        self.transaction.status = TransactionStatus.PENDING
        self.transaction.save()
        
        self.client.force_login(self.admin_user)
        
        response = self.client.post(
            f'/api/ledger/transactions/{self.transaction.id}/approve'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['transaction']['status'], 'APPROVED')
    
    def test_staff_cannot_approve(self):
        """Test staff cannot approve transactions."""
        self.transaction.status = TransactionStatus.PENDING
        self.transaction.save()
        
        self.client.force_login(self.staff_user)
        
        response = self.client.post(
            f'/api/ledger/transactions/{self.transaction.id}/approve'
        )
        
        # Should be forbidden
        self.assertEqual(response.status_code, 403)


class AnalyticsAPITest(TestCase):
    """Test analytics API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.org_id = uuid4()
        
        self.user = User.objects.create_user(
            username='analyst',
            email='analyst@test.com',
            password='testpass123',
            org_id=self.org_id,
            role=UserRole.BOARD,
        )
        
        # Create some approved transactions
        Transaction.objects.create(
            org_id=self.org_id,
            transaction_type=TransactionType.INCOME,
            status=TransactionStatus.APPROVED,
            gross_amount=Decimal('5000.00'),
            net_amount=Decimal('5000.00'),
            amount=Decimal('5000.00'),
            category='Dues',
            transaction_date=date.today(),
        )
        
        Transaction.objects.create(
            org_id=self.org_id,
            transaction_type=TransactionType.EXPENSE,
            status=TransactionStatus.APPROVED,
            gross_amount=Decimal('2000.00'),
            net_amount=Decimal('2000.00'),
            amount=Decimal('2000.00'),
            category='Utilities',
            transaction_date=date.today(),
        )
    
    def test_get_financial_summary(self):
        """Test getting financial summary."""
        self.client.force_login(self.user)
        
        response = self.client.get('/api/ledger/analytics/summary?period=MTD')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['period'], 'MTD')
        self.assertEqual(Decimal(data['total_income']), Decimal('5000.00'))
        self.assertEqual(Decimal(data['total_expense']), Decimal('2000.00'))
        self.assertEqual(Decimal(data['net_balance']), Decimal('3000.00'))
    
    def test_get_profit_loss_status(self):
        """Test getting profit/loss status."""
        self.client.force_login(self.user)
        
        response = self.client.get('/api/ledger/analytics/profit-loss?period=MTD')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_profitable'])


class CategoryConfigAPITest(TestCase):
    """Test category configuration API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.org_id = uuid4()
        
        # Board can manage config
        self.board_user = User.objects.create_user(
            username='board',
            email='board@test.com',
            password='testpass123',
            org_id=self.org_id,
            role=UserRole.BOARD,
        )
        
        # Create some categories
        TransactionCategory.objects.create(
            org_id=self.org_id,
            name='Test Income',
            transaction_type=TransactionType.INCOME,
        )
    
    def test_list_categories(self):
        """Test listing categories."""
        self.client.force_login(self.board_user)
        
        response = self.client.get('/api/ledger/categories')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data), 0)
    
    def test_create_category(self):
        """Test creating a category."""
        self.client.force_login(self.board_user)
        
        payload = {
            'name': 'New Category',
            'transaction_type': 'EXPENSE',
            'description': 'Test category',
        }
        
        response = self.client.post(
            '/api/ledger/categories',
            data=json.dumps(payload),
            content_type='application/json',
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['name'], 'New Category')
