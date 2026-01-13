"""
Unit tests for ledger services.
Tests core business logic including validation, penalty calculation, and credit management.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from uuid import uuid4
from django.test import TestCase

from apps.ledger.models import (
    Transaction, TransactionCategory, TransactionType, TransactionStatus,
    PaymentType, DiscountConfig, DiscountType, PenaltyPolicy,
    DuesStatement, DuesStatementStatus, UnitCredit, CreditTransaction,
)
from apps.ledger import services
from apps.ledger.dtos import ValidationResultDTO


class SimpleInterestCalculationTest(TestCase):
    """Test simple interest penalty calculation."""
    
    def test_simple_interest_calculation_basic(self):
        """Test I = P × R × T formula."""
        # Principal: 1000, Rate: 2% (0.02), Time: 3 months
        # Expected: 1000 × 0.02 × 3 = 60
        result = services.calculate_simple_interest_penalty(
            principal=Decimal('1000.00'),
            monthly_rate=Decimal('0.02'),
            months_overdue=3,
        )
        self.assertEqual(result, Decimal('60.00'))
    
    def test_simple_interest_with_different_rates(self):
        """Test with various interest rates."""
        # 1% monthly rate
        result = services.calculate_simple_interest_penalty(
            principal=Decimal('5000.00'),
            monthly_rate=Decimal('0.01'),
            months_overdue=2,
        )
        self.assertEqual(result, Decimal('100.00'))
        
        # 0.5% monthly rate
        result = services.calculate_simple_interest_penalty(
            principal=Decimal('2000.00'),
            monthly_rate=Decimal('0.005'),
            months_overdue=4,
        )
        self.assertEqual(result, Decimal('40.00'))
    
    def test_simple_interest_zero_months(self):
        """Test with zero months - should return 0."""
        result = services.calculate_simple_interest_penalty(
            principal=Decimal('1000.00'),
            monthly_rate=Decimal('0.02'),
            months_overdue=0,
        )
        self.assertEqual(result, Decimal('0.00'))
    
    def test_simple_interest_negative_months(self):
        """Test with negative months - should return 0."""
        result = services.calculate_simple_interest_penalty(
            principal=Decimal('1000.00'),
            monthly_rate=Decimal('0.02'),
            months_overdue=-1,
        )
        self.assertEqual(result, Decimal('0.00'))


class TransactionValidationTest(TestCase):
    """Test transaction validation logic."""
    
    def test_validate_positive_amount(self):
        """Test that positive amounts pass validation."""
        result = services.validate_transaction(
            org_id=uuid4(),
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal('100.00'),
        )
        self.assertTrue(result.valid)
    
    def test_validate_zero_amount_fails(self):
        """Test that zero amount fails validation."""
        result = services.validate_transaction(
            org_id=uuid4(),
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal('0.00'),
        )
        self.assertFalse(result.valid)
        self.assertIn("positive", result.error.lower())
    
    def test_validate_negative_amount_fails(self):
        """Test that negative amount fails validation."""
        result = services.validate_transaction(
            org_id=uuid4(),
            transaction_type=TransactionType.EXPENSE,
            amount=Decimal('-50.00'),
        )
        self.assertFalse(result.valid)


class CreditServicesTest(TestCase):
    """Test credit management services."""
    
    def setUp(self):
        """Set up test data."""
        self.org_id = uuid4()
        self.unit_id = uuid4()
    
    def test_get_or_create_unit_credit(self):
        """Test creating a new credit account."""
        credit = services.get_or_create_unit_credit(self.org_id, self.unit_id)
        
        self.assertIsNotNone(credit)
        self.assertEqual(credit.unit_id, self.unit_id)
        self.assertEqual(credit.credit_balance, Decimal('0.00'))
    
    def test_add_credit(self):
        """Test adding credit to a unit."""
        # Add credit
        credit_txn = services.add_credit(
            org_id=self.org_id,
            unit_id=self.unit_id,
            amount=Decimal('5000.00'),
            description="Advance payment",
        )
        
        self.assertIsNotNone(credit_txn)
        self.assertEqual(credit_txn.amount, Decimal('5000.00'))
        self.assertEqual(credit_txn.balance_after, Decimal('5000.00'))
        
        # Check balance
        balance = services.get_credit_balance(self.unit_id)
        self.assertEqual(balance, Decimal('5000.00'))
    
    def test_deduct_credit_success(self):
        """Test successful credit deduction."""
        # First add credit
        services.add_credit(
            org_id=self.org_id,
            unit_id=self.unit_id,
            amount=Decimal('3000.00'),
        )
        
        # Then deduct
        credit_txn = services.deduct_credit(
            org_id=self.org_id,
            unit_id=self.unit_id,
            amount=Decimal('1000.00'),
        )
        
        self.assertIsNotNone(credit_txn)
        self.assertEqual(credit_txn.amount, Decimal('-1000.00'))
        self.assertEqual(credit_txn.balance_after, Decimal('2000.00'))
    
    def test_deduct_credit_insufficient_balance(self):
        """Test deduction fails with insufficient balance."""
        # Add small credit
        services.add_credit(
            org_id=self.org_id,
            unit_id=self.unit_id,
            amount=Decimal('500.00'),
        )
        
        # Try to deduct more than available
        result = services.deduct_credit(
            org_id=self.org_id,
            unit_id=self.unit_id,
            amount=Decimal('1000.00'),
        )
        
        # Should return None for insufficient balance
        self.assertIsNone(result)
        
        # Balance should be unchanged
        balance = services.get_credit_balance(self.unit_id)
        self.assertEqual(balance, Decimal('500.00'))
    
    def test_get_credit_balance_nonexistent(self):
        """Test getting balance for unit with no credit account."""
        balance = services.get_credit_balance(uuid4())
        self.assertEqual(balance, Decimal('0.00'))


class DiscountCalculationTest(TestCase):
    """Test discount calculation services."""
    
    def setUp(self):
        """Set up test data."""
        self.org_id = uuid4()
        
        # Create discount configurations
        self.percentage_discount = DiscountConfig.objects.create(
            org_id=self.org_id,
            name="10% Early Payment",
            discount_type=DiscountType.PERCENTAGE,
            value=Decimal('10.00'),
            min_months=1,
            is_active=True,
        )
        
        self.flat_discount = DiscountConfig.objects.create(
            org_id=self.org_id,
            name="₱500 Promo",
            discount_type=DiscountType.FLAT,
            value=Decimal('500.00'),
            min_months=1,
            is_active=True,
        )
    
    def test_calculate_percentage_discount(self):
        """Test percentage discount calculation."""
        discounts = services.calculate_applicable_discounts(
            org_id=self.org_id,
            category_id=None,
            amount=Decimal('5000.00'),
            months=1,
        )
        
        # Find the percentage discount
        percentage = next((d for d in discounts if d.discount_type == 'PERCENTAGE'), None)
        self.assertIsNotNone(percentage)
        # 10% of 5000 = 500
        self.assertEqual(percentage.calculated_amount, Decimal('500.00'))
    
    def test_calculate_flat_discount(self):
        """Test flat discount calculation."""
        discounts = services.calculate_applicable_discounts(
            org_id=self.org_id,
            category_id=None,
            amount=Decimal('5000.00'),
            months=1,
        )
        
        # Find the flat discount
        flat = next((d for d in discounts if d.discount_type == 'FLAT'), None)
        self.assertIsNotNone(flat)
        self.assertEqual(flat.calculated_amount, Decimal('500.00'))


class PenaltyPolicyTest(TestCase):
    """Test penalty policy model and calculation."""
    
    def test_penalty_policy_percentage_calculation(self):
        """Test penalty calculation using percentage rate."""
        policy = PenaltyPolicy(
            org_id=uuid4(),
            name="Test Penalty",
            rate_type='PERCENT',
            rate_value=Decimal('2.00'),  # 2% monthly
            grace_period_days=15,
        )
        
        # Calculate penalty: 1000 × 0.02 × 3 = 60
        penalty = policy.calculate_penalty(
            principal=Decimal('1000.00'),
            months_overdue=3,
        )
        
        self.assertEqual(penalty, Decimal('60.00'))
    
    def test_penalty_policy_flat_calculation(self):
        """Test penalty calculation using flat rate."""
        policy = PenaltyPolicy(
            org_id=uuid4(),
            name="Test Flat Penalty",
            rate_type='FLAT',
            rate_value=Decimal('100.00'),  # 100 per month
            grace_period_days=15,
        )
        
        # Calculate penalty: 100 × 3 = 300
        penalty = policy.calculate_penalty(
            principal=Decimal('1000.00'),  # Principal ignored for flat
            months_overdue=3,
        )
        
        self.assertEqual(penalty, Decimal('300.00'))
