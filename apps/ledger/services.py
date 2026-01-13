"""
Core services for Ledger app.
Handles transaction operations, validation, and cross-app communication.
"""
from typing import List, Optional, Tuple
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from django.db.models import Sum, Q
from django.utils import timezone

from apps.registry.services import get_unit_dto
from .models import (
    Transaction, TransactionType, TransactionStatus, PaymentType,
    TransactionCategory, TransactionAttachment, TransactionAdjustment,
    AdjustmentType, DiscountConfig, PenaltyPolicy, DuesStatement,
    DuesStatementStatus, UnitCredit, CreditTransaction, CreditTransactionType,
)
from .dtos import (
    TransactionDTO, TransactionDetailDTO, TransactionBreakdownDTO,
    AdjustmentPreviewDTO, DiscountPreviewDTO, PenaltyPreviewDTO,
    ValidationResultDTO, UnitCreditDTO, CreditTransactionDTO, DuesStatementDTO,
)


# =============================================================================
# Transaction DTO Helpers
# =============================================================================

def get_transaction_dto(transaction_id: UUID) -> Optional[TransactionDTO]:
    """Get a transaction DTO by ID."""
    try:
        txn = Transaction.objects.get(id=transaction_id)
        return TransactionDTO(
            id=txn.id,
            org_id=txn.org_id,
            transaction_type=txn.transaction_type,
            status=txn.status,
            amount=txn.amount,
            net_amount=txn.net_amount,
            category=txn.category,
            transaction_date=txn.transaction_date,
        )
    except Transaction.DoesNotExist:
        return None


def get_transaction_detail_dto(transaction_id: UUID) -> Optional[TransactionDetailDTO]:
    """Get detailed transaction DTO by ID."""
    try:
        txn = Transaction.objects.get(id=transaction_id)
        return TransactionDetailDTO(
            id=txn.id,
            org_id=txn.org_id,
            unit_id=txn.unit_id,
            category_id=txn.category_id,
            transaction_type=txn.transaction_type,
            status=txn.status,
            payment_type=txn.payment_type,
            gross_amount=txn.gross_amount,
            net_amount=txn.net_amount,
            category=txn.category,
            description=txn.description,
            payer_name=txn.payer_name,
            reference_number=txn.reference_number,
            transaction_date=txn.transaction_date,
            requires_receipt=txn.requires_receipt,
            receipt_verified=txn.receipt_verified,
            created_by_id=txn.created_by_id,
            approved_by_id=txn.approved_by_id,
            approved_at=txn.approved_at,
            created_at=txn.created_at,
        )
    except Transaction.DoesNotExist:
        return None


# =============================================================================
# Validation Services
# =============================================================================

def validate_transaction(
    org_id: UUID,
    transaction_type: str,
    amount: Decimal,
    category_id: Optional[UUID] = None,
    unit_id: Optional[UUID] = None,
    requires_receipt: bool = False,
    has_receipt: bool = False,
) -> ValidationResultDTO:
    """
    Validate a transaction before creation.
    
    Checks:
    - Amount is positive
    - Category exists and is active
    - Unit exists and is active (if provided)
    - Receipt is attached (if required)
    """
    # Amount validation
    if amount <= 0:
        return ValidationResultDTO(valid=False, error="Amount must be positive")
    
    # Category validation
    if category_id:
        try:
            category = TransactionCategory.objects.get(
                id=category_id, 
                org_id=org_id, 
                is_active=True,
                transaction_type=transaction_type
            )
        except TransactionCategory.DoesNotExist:
            return ValidationResultDTO(
                valid=False, 
                error="Invalid or inactive category for this transaction type"
            )
    
    # Unit validation (for income transactions)
    if unit_id:
        unit_dto = get_unit_dto(unit_id)
        if not unit_dto:
            return ValidationResultDTO(valid=False, error="Unit not found")
        if not unit_dto.is_active:
            return ValidationResultDTO(valid=False, error="Unit is inactive")
    
    # Receipt requirement
    if requires_receipt and not has_receipt:
        return ValidationResultDTO(
            valid=False, 
            error="Receipt attachment is required for this transaction"
        )
    
    return ValidationResultDTO(valid=True)


def validate_payment_amount(
    unit_id: UUID,
    amount: Decimal,
    payment_type: str,
    org_id: UUID,
) -> ValidationResultDTO:
    """
    Validates that payment amount matches what is due.
    
    CRITICAL: Prevents overcollection - staff cannot collect more than owed
    unless the transaction is marked as Advance Payment.
    
    Rules:
    1. If payment_type == 'EXACT': amount MUST equal total_due (base + penalties)
    2. If payment_type == 'ADVANCE': amount can be greater (excess goes to credit)
    3. Amount can NEVER be less than what is due (partial payments not allowed)
    """
    # Get current dues for the unit
    current_dues = get_current_dues_for_unit(org_id, unit_id)
    
    if not current_dues:
        # No outstanding dues - only advance payment allowed
        if payment_type == PaymentType.EXACT:
            return ValidationResultDTO(
                valid=False,
                error="No outstanding dues found. Use Advance Payment for credit deposits."
            )
        # Advance payment with no dues - all goes to credit
        return ValidationResultDTO(valid=True, credit_to_add=amount)
    
    total_due = current_dues.net_amount - current_dues.amount_paid
    
    if amount < total_due:
        return ValidationResultDTO(
            valid=False,
            error=f"Minimum payment is ₱{total_due:.2f}. Partial payments are not allowed."
        )
    
    if payment_type == PaymentType.EXACT:
        if amount != total_due:
            return ValidationResultDTO(
                valid=False,
                error=f"Exact payment must be ₱{total_due:.2f}. Received: ₱{amount:.2f}"
            )
        return ValidationResultDTO(valid=True)
    
    elif payment_type == PaymentType.ADVANCE:
        # Excess goes to credit
        excess = amount - total_due
        return ValidationResultDTO(valid=True, credit_to_add=excess if excess > 0 else None)
    
    return ValidationResultDTO(valid=True)


# =============================================================================
# Penalty Calculation Services (Simple Interest)
# =============================================================================

def calculate_simple_interest_penalty(
    principal: Decimal,
    monthly_rate: Decimal,
    months_overdue: int,
) -> Decimal:
    """
    Calculate penalty using Simple Interest: I = P × R × T
    
    Args:
        principal: The unpaid dues amount
        monthly_rate: Monthly interest rate as decimal (e.g., 0.02 for 2%)
        months_overdue: Number of months overdue
        
    Returns:
        Decimal: The penalty amount
    """
    if months_overdue <= 0:
        return Decimal('0.00')
    
    return (principal * monthly_rate * months_overdue).quantize(Decimal('0.01'))


def calculate_pending_penalties(
    org_id: UUID,
    unit_id: UUID,
) -> List[PenaltyPreviewDTO]:
    """
    Calculate all pending penalties for a unit based on overdue statements.
    Uses Simple Interest calculation.
    """
    penalties = []
    
    # Get active penalty policy for the org
    try:
        policy = PenaltyPolicy.objects.get(org_id=org_id, is_active=True)
    except PenaltyPolicy.DoesNotExist:
        return penalties
    
    # Get overdue statements
    overdue_statements = DuesStatement.objects.filter(
        org_id=org_id,
        unit_id=unit_id,
        status__in=[DuesStatementStatus.UNPAID, DuesStatementStatus.OVERDUE],
        due_date__lt=timezone.now().date(),
    )
    
    today = timezone.now().date()
    
    for statement in overdue_statements:
        # Calculate months overdue (after grace period)
        days_overdue = (today - statement.due_date).days
        days_after_grace = days_overdue - policy.grace_period_days
        
        if days_after_grace > 0:
            # Approximate months overdue (30 days = 1 month)
            months_overdue = max(1, days_after_grace // 30)
            
            principal = statement.net_amount - statement.amount_paid
            
            if policy.rate_type == 'PERCENT':
                rate = policy.rate_value / Decimal('100')
                penalty_amount = calculate_simple_interest_penalty(
                    principal, rate, months_overdue
                )
            else:
                # Flat fee per month
                penalty_amount = policy.rate_value * months_overdue
            
            penalties.append(PenaltyPreviewDTO(
                name=f"{policy.name} ({statement.statement_month}/{statement.statement_year})",
                principal=principal,
                rate=policy.rate_value,
                months_overdue=months_overdue,
                calculated_amount=penalty_amount,
            ))
    
    return penalties


# =============================================================================
# Discount Calculation Services
# =============================================================================

def calculate_applicable_discounts(
    org_id: UUID,
    category_id: Optional[UUID],
    amount: Decimal,
    months: int = 1,
) -> List[DiscountPreviewDTO]:
    """
    Find applicable discounts for a transaction.
    """
    discounts = []
    today = timezone.now().date()
    
    # Get active discounts
    queryset = DiscountConfig.objects.filter(
        org_id=org_id,
        is_active=True,
        min_months__lte=months,
    )
    
    # Filter by validity dates
    queryset = queryset.filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=today),
        Q(valid_until__isnull=True) | Q(valid_until__gte=today),
    )
    
    for discount in queryset:
        # Check category applicability
        if discount.applicable_categories:
            if category_id and str(category_id) not in discount.applicable_categories:
                continue
        
        # Calculate discount amount
        if discount.discount_type == 'PERCENTAGE':
            calculated = (amount * discount.value / Decimal('100')).quantize(Decimal('0.01'))
        else:
            calculated = discount.value
        
        discounts.append(DiscountPreviewDTO(
            id=discount.id,
            name=discount.name,
            discount_type=discount.discount_type,
            value=discount.value,
            calculated_amount=calculated,
        ))
    
    return discounts


# =============================================================================
# Transaction Breakdown Preview
# =============================================================================

def preview_transaction_breakdown(
    org_id: UUID,
    unit_id: Optional[UUID],
    amount: Decimal,
    payment_type: str,
    category_id: Optional[UUID] = None,
    apply_discount_ids: Optional[List[UUID]] = None,
    months: int = 1,
) -> TransactionBreakdownDTO:
    """
    Generate a complete breakdown of a transaction before submission.
    Shows gross amount, penalties, discounts, and final net amount.
    """
    gross_amount = amount
    adjustments = []
    
    # Calculate penalties (for income transactions with unit)
    pending_penalties = []
    if unit_id:
        pending_penalties = calculate_pending_penalties(org_id, unit_id)
        
        # Add penalties to adjustments
        for penalty in pending_penalties:
            adjustments.append(AdjustmentPreviewDTO(
                adjustment_type=AdjustmentType.PENALTY,
                amount=penalty.calculated_amount,
                reason=penalty.name,
                months_overdue=penalty.months_overdue,
            ))
    
    # Get applicable discounts
    applicable_discounts = calculate_applicable_discounts(
        org_id, category_id, amount, months
    )
    
    # Apply selected discounts
    applied_discounts = []
    if apply_discount_ids:
        for discount in applicable_discounts:
            if discount.id in apply_discount_ids:
                adjustments.append(AdjustmentPreviewDTO(
                    adjustment_type=AdjustmentType.DISCOUNT,
                    amount=discount.calculated_amount,
                    reason=discount.name,
                ))
                applied_discounts.append(discount)
    
    # Calculate net amount
    total_penalties = sum(
        adj.amount for adj in adjustments 
        if adj.adjustment_type == AdjustmentType.PENALTY
    )
    total_discounts = sum(
        adj.amount for adj in adjustments 
        if adj.adjustment_type == AdjustmentType.DISCOUNT
    )
    
    net_amount = gross_amount + total_penalties - total_discounts
    
    # Calculate credit to add for advance payments
    credit_to_add = None
    if payment_type == PaymentType.ADVANCE and unit_id:
        current_dues = get_current_dues_for_unit(org_id, unit_id)
        if current_dues:
            total_due = current_dues.net_amount - current_dues.amount_paid + total_penalties
            if net_amount > total_due:
                credit_to_add = net_amount - total_due
    
    return TransactionBreakdownDTO(
        gross_amount=gross_amount,
        adjustments=adjustments,
        pending_penalties=pending_penalties,
        applicable_discounts=applicable_discounts,
        net_amount=net_amount,
        credit_to_add=credit_to_add,
    )


# =============================================================================
# Dues Statement Services
# =============================================================================

def get_current_dues_for_unit(org_id: UUID, unit_id: UUID) -> Optional[DuesStatement]:
    """Get the current/oldest unpaid dues statement for a unit."""
    return DuesStatement.objects.filter(
        org_id=org_id,
        unit_id=unit_id,
        status__in=[DuesStatementStatus.UNPAID, DuesStatementStatus.OVERDUE, DuesStatementStatus.PARTIAL],
    ).order_by('statement_year', 'statement_month').first()


def get_dues_statement_dto(statement: DuesStatement) -> DuesStatementDTO:
    """Convert DuesStatement to DTO."""
    return DuesStatementDTO(
        id=statement.id,
        org_id=statement.org_id,
        unit_id=statement.unit_id,
        statement_month=statement.statement_month,
        statement_year=statement.statement_year,
        base_amount=statement.base_amount,
        penalty_amount=statement.penalty_amount,
        discount_amount=statement.discount_amount,
        net_amount=statement.net_amount,
        amount_paid=statement.amount_paid,
        balance_due=statement.balance_due,
        status=statement.status,
        due_date=statement.due_date,
        paid_date=statement.paid_date,
    )


# =============================================================================
# Credit Services
# =============================================================================

def get_or_create_unit_credit(org_id: UUID, unit_id: UUID) -> UnitCredit:
    """Get or create a credit account for a unit."""
    credit, created = UnitCredit.objects.get_or_create(
        unit_id=unit_id,
        defaults={'org_id': org_id, 'credit_balance': Decimal('0.00')}
    )
    return credit


def add_credit(
    org_id: UUID,
    unit_id: UUID,
    amount: Decimal,
    transaction_id: Optional[UUID] = None,
    description: str = "",
    created_by_id: Optional[UUID] = None,
) -> CreditTransaction:
    """
    Add credit to a unit's balance.
    Used for advance payments.
    """
    credit_account = get_or_create_unit_credit(org_id, unit_id)
    
    # Update balance
    credit_account.credit_balance += amount
    credit_account.save()
    
    # Log transaction
    credit_txn = CreditTransaction.objects.create(
        unit_credit_id=credit_account.id,
        transaction_id=transaction_id,
        transaction_type=CreditTransactionType.DEPOSIT,
        amount=amount,
        balance_after=credit_account.credit_balance,
        description=description or "Advance payment deposit",
        created_by_id=created_by_id,
    )
    
    return credit_txn


def deduct_credit(
    org_id: UUID,
    unit_id: UUID,
    amount: Decimal,
    transaction_id: Optional[UUID] = None,
    description: str = "",
    created_by_id: Optional[UUID] = None,
) -> Optional[CreditTransaction]:
    """
    Deduct credit from a unit's balance.
    Used when processing monthly dues.
    
    Returns None if insufficient balance.
    """
    credit_account = get_or_create_unit_credit(org_id, unit_id)
    
    if credit_account.credit_balance < amount:
        return None
    
    # Update balance
    credit_account.credit_balance -= amount
    credit_account.save()
    
    # Log transaction
    credit_txn = CreditTransaction.objects.create(
        unit_credit_id=credit_account.id,
        transaction_id=transaction_id,
        transaction_type=CreditTransactionType.DUES_DEDUCTION,
        amount=-amount,  # Negative for deductions
        balance_after=credit_account.credit_balance,
        description=description or "Monthly dues deduction",
        created_by_id=created_by_id,
    )
    
    return credit_txn


def get_credit_balance(unit_id: UUID) -> Decimal:
    """Get the current credit balance for a unit."""
    try:
        credit = UnitCredit.objects.get(unit_id=unit_id)
        return credit.credit_balance
    except UnitCredit.DoesNotExist:
        return Decimal('0.00')


def get_credit_balance_dto(unit_id: UUID) -> Optional[UnitCreditDTO]:
    """Get credit balance as DTO."""
    try:
        credit = UnitCredit.objects.get(unit_id=unit_id)
        return UnitCreditDTO(
            unit_id=credit.unit_id,
            credit_balance=credit.credit_balance,
            last_updated=credit.last_updated,
        )
    except UnitCredit.DoesNotExist:
        return None


def get_credit_history(unit_id: UUID, limit: int = 50) -> List[CreditTransactionDTO]:
    """Get credit transaction history for a unit."""
    try:
        credit = UnitCredit.objects.get(unit_id=unit_id)
    except UnitCredit.DoesNotExist:
        return []
    
    transactions = CreditTransaction.objects.filter(
        unit_credit_id=credit.id
    ).order_by('-created_at')[:limit]
    
    return [
        CreditTransactionDTO(
            id=txn.id,
            transaction_type=txn.transaction_type,
            amount=txn.amount,
            balance_after=txn.balance_after,
            description=txn.description,
            created_at=txn.created_at,
        )
        for txn in transactions
    ]


# =============================================================================
# Transaction CRUD Services (Legacy compatibility + new features)
# =============================================================================

def record_expense(
    org_id: UUID, 
    unit_id: Optional[UUID], 
    amount: Decimal, 
    category: str, 
    description: str, 
    transaction_date: date, 
    created_by_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    asset_id: Optional[UUID] = None,
) -> TransactionDTO:
    """
    Record an expense transaction.
    Legacy method maintained for backward compatibility.
    """
    # Validate unit if provided
    if unit_id:
        unit_dto = get_unit_dto(unit_id)
        if not unit_dto or not unit_dto.is_active:
            raise ValueError("Invalid or inactive unit")
    
    transaction = Transaction.objects.create(
        org_id=org_id,
        unit_id=unit_id,
        asset_id=asset_id,
        category_id=category_id,
        transaction_type=TransactionType.EXPENSE,
        status=TransactionStatus.DRAFT,
        payment_type=PaymentType.EXACT,
        gross_amount=amount,
        net_amount=amount,
        amount=amount,
        category=category,
        description=description,
        transaction_date=transaction_date,
        created_by_id=created_by_id,
    )
    
    return TransactionDTO(
        id=transaction.id,
        org_id=transaction.org_id,
        transaction_type=transaction.transaction_type,
        status=transaction.status,
        amount=transaction.amount,
        net_amount=transaction.net_amount,
        category=transaction.category,
        transaction_date=transaction.transaction_date,
    )


def record_income(
    org_id: UUID,
    amount: Decimal,
    category: str,
    description: str,
    transaction_date: date,
    payment_type: str = PaymentType.EXACT,
    unit_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    payer_name: Optional[str] = None,
    reference_number: Optional[str] = None,
    apply_discount_ids: Optional[List[UUID]] = None,
    created_by_id: Optional[UUID] = None,
) -> Tuple[TransactionDTO, Optional[Decimal]]:
    """
    Record an income transaction.
    
    Returns:
        Tuple of (TransactionDTO, credit_to_add) where credit_to_add
        is the amount added to unit credit for advance payments.
    """
    # Validate payment amount if unit specified
    if unit_id:
        validation = validate_payment_amount(unit_id, amount, payment_type, org_id)
        if not validation.valid:
            raise ValueError(validation.error)
    
    # Get breakdown for adjustments
    breakdown = preview_transaction_breakdown(
        org_id=org_id,
        unit_id=unit_id,
        amount=amount,
        payment_type=payment_type,
        category_id=category_id,
        apply_discount_ids=apply_discount_ids,
    )
    
    # Create transaction
    transaction = Transaction.objects.create(
        org_id=org_id,
        unit_id=unit_id,
        category_id=category_id,
        transaction_type=TransactionType.INCOME,
        status=TransactionStatus.DRAFT,
        payment_type=payment_type,
        gross_amount=breakdown.gross_amount,
        net_amount=breakdown.net_amount,
        amount=breakdown.net_amount,
        category=category,
        description=description,
        payer_name=payer_name,
        reference_number=reference_number,
        transaction_date=transaction_date,
        created_by_id=created_by_id,
    )
    
    # Create adjustment records
    for adjustment in breakdown.adjustments:
        TransactionAdjustment.objects.create(
            transaction_id=transaction.id,
            adjustment_type=adjustment.adjustment_type,
            amount=adjustment.amount,
            reason=adjustment.reason,
            penalty_months=adjustment.months_overdue,
            created_by_id=created_by_id,
        )
    
    dto = TransactionDTO(
        id=transaction.id,
        org_id=transaction.org_id,
        transaction_type=transaction.transaction_type,
        status=transaction.status,
        amount=transaction.amount,
        net_amount=transaction.net_amount,
        category=transaction.category,
        transaction_date=transaction.transaction_date,
    )
    
    return dto, breakdown.credit_to_add


# =============================================================================
# Transaction Listing
# =============================================================================

def list_transactions(
    org_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[UUID] = None,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    unit_id: Optional[UUID] = None,
    limit: int = 100,
) -> List[TransactionDTO]:
    """
    List transactions with filtering.
    """
    queryset = Transaction.objects.filter(org_id=org_id)
    
    if start_date:
        queryset = queryset.filter(transaction_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(transaction_date__lte=end_date)
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if transaction_type:
        queryset = queryset.filter(transaction_type=transaction_type)
    if status:
        queryset = queryset.filter(status=status)
    if unit_id:
        queryset = queryset.filter(unit_id=unit_id)
    
    transactions = queryset[:limit]
    
    return [
        TransactionDTO(
            id=txn.id,
            org_id=txn.org_id,
            transaction_type=txn.transaction_type,
            status=txn.status,
            amount=txn.amount,
            net_amount=txn.net_amount,
            category=txn.category,
            transaction_date=txn.transaction_date,
        )
        for txn in transactions
    ]


# =============================================================================
# Approval Workflow
# =============================================================================

def submit_for_approval(
    transaction_id: UUID,
    submitted_by_id: UUID,
) -> TransactionDTO:
    """Submit a draft transaction for approval."""
    try:
        transaction = Transaction.objects.get(id=transaction_id)
    except Transaction.DoesNotExist:
        raise ValueError("Transaction not found")
    
    if transaction.status != TransactionStatus.DRAFT:
        raise ValueError(f"Cannot submit transaction with status: {transaction.status}")
    
    transaction.status = TransactionStatus.PENDING
    transaction.save()
    
    return get_transaction_dto(transaction_id)


def approve_transaction(
    transaction_id: UUID,
    approved_by_id: UUID,
    unit_id: Optional[UUID] = None,
) -> Tuple[TransactionDTO, Optional[Decimal]]:
    """
    Approve a pending transaction.
    If it's an advance payment, add credit to the unit.
    
    Returns:
        Tuple of (TransactionDTO, credit_added)
    """
    try:
        transaction = Transaction.objects.get(id=transaction_id)
    except Transaction.DoesNotExist:
        raise ValueError("Transaction not found")
    
    if transaction.status != TransactionStatus.PENDING:
        raise ValueError(f"Cannot approve transaction with status: {transaction.status}")
    
    transaction.status = TransactionStatus.APPROVED
    transaction.approved_by_id = approved_by_id
    transaction.approved_at = timezone.now()
    transaction.save()
    
    credit_added = None
    
    # Handle advance payment credit
    if (transaction.transaction_type == TransactionType.INCOME and 
        transaction.payment_type == PaymentType.ADVANCE and
        transaction.unit_id):
        
        # Calculate credit to add
        current_dues = get_current_dues_for_unit(transaction.org_id, transaction.unit_id)
        if current_dues:
            total_due = current_dues.net_amount - current_dues.amount_paid
            if transaction.net_amount > total_due:
                credit_added = transaction.net_amount - total_due
                add_credit(
                    org_id=transaction.org_id,
                    unit_id=transaction.unit_id,
                    amount=credit_added,
                    transaction_id=transaction.id,
                    description=f"Advance payment credit from transaction {transaction.id}",
                    created_by_id=approved_by_id,
                )
                
                # Mark dues as paid
                current_dues.status = DuesStatementStatus.PAID
                current_dues.amount_paid = current_dues.net_amount
                current_dues.paid_date = transaction.transaction_date
                current_dues.payment_transaction_id = transaction.id
                current_dues.save()
    
    return get_transaction_dto(transaction_id), credit_added


def reject_transaction(
    transaction_id: UUID,
    rejected_by_id: UUID,
    reason: str = "",
) -> TransactionDTO:
    """Reject a pending transaction (returns to draft)."""
    try:
        transaction = Transaction.objects.get(id=transaction_id)
    except Transaction.DoesNotExist:
        raise ValueError("Transaction not found")
    
    if transaction.status != TransactionStatus.PENDING:
        raise ValueError(f"Cannot reject transaction with status: {transaction.status}")
    
    transaction.status = TransactionStatus.DRAFT
    if reason:
        transaction.description = f"{transaction.description}\n[REJECTED: {reason}]"
    transaction.save()
    
    return get_transaction_dto(transaction_id)


def cancel_transaction(
    transaction_id: UUID,
    cancelled_by_id: UUID,
    reason: str = "",
) -> TransactionDTO:
    """Cancel a transaction."""
    try:
        transaction = Transaction.objects.get(id=transaction_id)
    except Transaction.DoesNotExist:
        raise ValueError("Transaction not found")
    
    if transaction.status == TransactionStatus.CANCELLED:
        raise ValueError("Transaction is already cancelled")
    
    transaction.status = TransactionStatus.CANCELLED
    if reason:
        transaction.description = f"{transaction.description}\n[CANCELLED: {reason}]"
    transaction.save()
    
    return get_transaction_dto(transaction_id)
