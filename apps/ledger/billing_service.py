"""
Billing Engine Service.
Handles monthly dues statement generation, credit application, and penalty calculation.
"""
from decimal import Decimal
from datetime import date
from typing import Optional, Tuple, List
from uuid import UUID
from django.utils import timezone
from django.db import transaction as db_transaction

from .models import (
    BillingConfig, DuesStatement, DuesStatementStatus,
    PenaltyPolicy, DiscountConfig, Transaction, TransactionType,
)
from .services import (
    get_or_create_unit_credit, deduct_credit, record_income,
    calculate_applicable_discounts, get_credit_balance,
)


def get_billing_config(org_id: UUID) -> Optional[BillingConfig]:
    """Get active billing configuration for an organization."""
    return BillingConfig.objects.filter(org_id=org_id, is_active=True).first()


def calculate_carried_penalties(org_id: UUID, unit_id: UUID) -> Decimal:
    """
    Calculate total penalties from past unpaid dues statements.
    Uses Simple Interest: I = P × R × T
    """
    unpaid_statements = DuesStatement.objects.filter(
        org_id=org_id,
        unit_id=unit_id,
        status__in=[DuesStatementStatus.PENDING, DuesStatementStatus.PARTIAL],
    )
    
    total_penalty = Decimal('0.00')
    penalty_policy = PenaltyPolicy.objects.filter(org_id=org_id, is_active=True).first()
    
    if not penalty_policy:
        return total_penalty
    
    today = timezone.now().date()
    
    for statement in unpaid_statements:
        # Calculate months overdue
        if statement.due_date and statement.due_date < today:
            days_overdue = (today - statement.due_date).days
            if days_overdue > penalty_policy.grace_period_days:
                months_overdue = max(1, days_overdue // 30)
                balance_due = statement.net_amount - statement.amount_paid
                penalty = penalty_policy.calculate_penalty(balance_due, months_overdue)
                total_penalty += penalty
    
    return total_penalty


def apply_credit_to_statement(
    org_id: UUID,
    unit_id: UUID,
    statement: DuesStatement,
) -> Tuple[Decimal, Optional[Transaction]]:
    """
    Apply available unit credit to a dues statement.
    Supports partial payment if credit < due amount.
    
    Returns:
        Tuple of (amount_paid, income_transaction or None)
    """
    credit_balance = get_credit_balance(unit_id)
    
    if credit_balance <= Decimal('0.00'):
        return Decimal('0.00'), None
    
    balance_due = statement.net_amount - statement.amount_paid
    amount_to_pay = min(credit_balance, balance_due)
    
    if amount_to_pay <= Decimal('0.00'):
        return Decimal('0.00'), None
    
    with db_transaction.atomic():
        # Deduct credit
        credit_txn = deduct_credit(
            org_id=org_id,
            unit_id=unit_id,
            amount=amount_to_pay,
            description=f"Dues payment for {statement.statement_month}/{statement.statement_year}",
        )
        
        if not credit_txn:
            return Decimal('0.00'), None
        
        # Update statement
        statement.amount_paid += amount_to_pay
        if statement.amount_paid >= statement.net_amount:
            statement.status = DuesStatementStatus.PAID
            statement.paid_date = timezone.now().date()
        else:
            statement.status = DuesStatementStatus.PARTIAL
        statement.save()
        
        # Record income transaction
        income_dto, _ = record_income(
            org_id=org_id,
            amount=amount_to_pay,
            category="Monthly Dues",
            description=f"Auto-deducted from credit for {statement.statement_month}/{statement.statement_year}",
            transaction_date=timezone.now().date(),
            payment_type='EXACT',
            unit_id=unit_id,
        )
        
        return amount_to_pay, income_dto


def generate_statement_for_unit(
    org_id: UUID,
    unit_id: UUID,
    billing_config: BillingConfig,
    statement_month: int,
    statement_year: int,
) -> Optional[DuesStatement]:
    """
    Generate a monthly dues statement for a single unit.
    Applies discounts and carried penalties.
    """
    # Check if statement already exists
    existing = DuesStatement.objects.filter(
        org_id=org_id,
        unit_id=unit_id,
        statement_month=statement_month,
        statement_year=statement_year,
    ).first()
    
    if existing:
        return existing
    
    base_amount = billing_config.monthly_dues_amount
    
    # Calculate applicable discounts
    discounts = calculate_applicable_discounts(
        org_id=org_id,
        category_id=None,
        amount=base_amount,
        months=1,
    )
    discount_amount = sum(d.calculated_amount for d in discounts)
    
    # Calculate carried penalties from past unpaid dues
    penalty_amount = calculate_carried_penalties(org_id, unit_id)
    
    # Calculate net amount
    net_amount = base_amount - discount_amount + penalty_amount
    
    # Calculate due date
    due_date = date(statement_year, statement_month, billing_config.billing_day)
    
    # Create statement
    statement = DuesStatement.objects.create(
        org_id=org_id,
        unit_id=unit_id,
        statement_month=statement_month,
        statement_year=statement_year,
        base_amount=base_amount,
        penalty_amount=penalty_amount,
        discount_amount=discount_amount,
        net_amount=net_amount,
        amount_paid=Decimal('0.00'),
        status=DuesStatementStatus.PENDING,
        due_date=due_date,
    )
    
    # Try to apply credit
    apply_credit_to_statement(org_id, unit_id, statement)
    
    return statement


def generate_monthly_statements(org_id: UUID) -> List[DuesStatement]:
    """
    Generate monthly dues statements for all active units in an organization.
    Called by the Celery periodic task.
    """
    from apps.registry.models import Unit
    
    billing_config = get_billing_config(org_id)
    if not billing_config:
        return []
    
    today = timezone.now().date()
    statement_month = today.month
    statement_year = today.year
    
    # Get all active units for this organization
    units = Unit.objects.filter(org_id=org_id, is_active=True)
    
    statements = []
    for unit in units:
        statement = generate_statement_for_unit(
            org_id=org_id,
            unit_id=unit.id,
            billing_config=billing_config,
            statement_month=statement_month,
            statement_year=statement_year,
        )
        if statement:
            statements.append(statement)
    
    return statements
