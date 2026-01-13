"""
API Schemas for Ledger app.
Pydantic/Ninja schemas for request/response validation.
"""
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime
from ninja import Schema


# =============================================================================
# Enums
# =============================================================================

class TransactionTypeEnum:
    INCOME = 'INCOME'
    EXPENSE = 'EXPENSE'


class TransactionStatusEnum:
    DRAFT = 'DRAFT'
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    CANCELLED = 'CANCELLED'


class PaymentTypeEnum:
    EXACT = 'EXACT'
    ADVANCE = 'ADVANCE'


# =============================================================================
# Request Schemas
# =============================================================================

class IncomeIn(Schema):
    """Schema for creating an income transaction."""
    unit_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    category: str
    amount: Decimal
    payment_type: str = PaymentTypeEnum.EXACT  # 'EXACT' or 'ADVANCE'
    description: str = ""
    payer_name: Optional[str] = None
    reference_number: Optional[str] = None
    transaction_date: date
    apply_discount_ids: Optional[List[UUID]] = None


class ExpenseIn(Schema):
    """Schema for creating an expense transaction."""
    category_id: Optional[UUID] = None
    category: str
    amount: Decimal
    description: str = ""
    transaction_date: date
    asset_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None


class TransactionUpdateIn(Schema):
    """Schema for updating a transaction."""
    category_id: Optional[UUID] = None
    category: Optional[str] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    payer_name: Optional[str] = None
    reference_number: Optional[str] = None
    transaction_date: Optional[date] = None


class TransactionApprovalIn(Schema):
    """Schema for approval workflow actions."""
    action: str  # 'submit', 'approve', 'reject', 'cancel'
    comment: Optional[str] = None


class BulkPaymentIn(Schema):
    """Schema for processing bulk dues payment."""
    unit_id: UUID
    amount: Decimal
    months: int
    discount_id: Optional[UUID] = None
    reference_number: Optional[str] = None
    transaction_date: date
    payer_name: Optional[str] = None


class PreviewBreakdownIn(Schema):
    """Schema for previewing transaction breakdown."""
    unit_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    amount: Decimal
    payment_type: str = PaymentTypeEnum.EXACT
    apply_discount_ids: Optional[List[UUID]] = None
    months: int = 1


class CategoryIn(Schema):
    """Schema for creating a transaction category."""
    name: str
    transaction_type: str  # 'INCOME' or 'EXPENSE'
    description: str = ""


class DiscountConfigIn(Schema):
    """Schema for creating a discount configuration."""
    name: str
    description: str = ""
    discount_type: str  # 'PERCENTAGE' or 'FLAT'
    value: Decimal
    applicable_categories: Optional[List[UUID]] = None
    min_months: int = 1
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None


class PenaltyPolicyIn(Schema):
    """Schema for creating a penalty policy."""
    name: str
    description: str = ""
    rate_type: str  # 'FLAT' or 'PERCENT'
    rate_value: Decimal
    grace_period_days: int = 15
    applicable_categories: Optional[List[UUID]] = None


class TransactionFilterIn(Schema):
    """Schema for filtering transactions."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    category_id: Optional[UUID] = None
    transaction_type: Optional[str] = None  # 'INCOME' or 'EXPENSE'
    status: Optional[str] = None
    unit_id: Optional[UUID] = None


class ReportFilterIn(Schema):
    """Schema for generating reports."""
    report_date: Optional[date] = None
    year: Optional[int] = None
    month: Optional[int] = None


# =============================================================================
# Response Schemas
# =============================================================================

class TransactionOut(Schema):
    """Basic transaction output."""
    id: UUID
    org_id: UUID
    transaction_type: str
    status: str
    amount: Decimal
    net_amount: Decimal
    category: str
    transaction_date: date


class TransactionDetailOut(Schema):
    """Detailed transaction output."""
    id: UUID
    org_id: UUID
    unit_id: Optional[UUID]
    category_id: Optional[UUID]
    transaction_type: str
    status: str
    payment_type: str
    gross_amount: Decimal
    net_amount: Decimal
    category: str
    description: str
    payer_name: Optional[str]
    reference_number: Optional[str]
    transaction_date: date
    requires_receipt: bool
    receipt_verified: bool
    created_by_id: Optional[UUID]
    approved_by_id: Optional[UUID]
    approved_at: Optional[datetime]
    created_at: datetime


class AdjustmentOut(Schema):
    """Adjustment output for breakdowns."""
    adjustment_type: str
    amount: Decimal
    reason: str
    months_overdue: Optional[int] = None


class DiscountPreviewOut(Schema):
    """Discount preview output."""
    id: UUID
    name: str
    discount_type: str
    value: Decimal
    calculated_amount: Decimal


class PenaltyPreviewOut(Schema):
    """Penalty preview output."""
    name: str
    principal: Decimal
    rate: Decimal
    months_overdue: int
    calculated_amount: Decimal


class TransactionBreakdownOut(Schema):
    """Complete breakdown output."""
    gross_amount: Decimal
    adjustments: List[AdjustmentOut]
    pending_penalties: List[PenaltyPreviewOut]
    applicable_discounts: List[DiscountPreviewOut]
    net_amount: Decimal
    credit_to_add: Optional[Decimal] = None


class CategoryOut(Schema):
    """Transaction category output."""
    id: UUID
    name: str
    transaction_type: str
    description: str
    is_active: bool
    is_default: bool


class DiscountConfigOut(Schema):
    """Discount configuration output."""
    id: UUID
    name: str
    description: str
    discount_type: str
    value: Decimal
    min_months: int
    is_active: bool


class PenaltyPolicyOut(Schema):
    """Penalty policy output."""
    id: UUID
    name: str
    description: str
    rate_type: str
    rate_value: Decimal
    grace_period_days: int
    is_active: bool


class AttachmentOut(Schema):
    """Transaction attachment output."""
    id: UUID
    transaction_id: UUID
    file_url: str
    file_name: str
    file_type: str
    file_size: int
    created_at: datetime
    _warning: Optional[str] = None  # For dev mode S3 warning


class CreditBalanceOut(Schema):
    """Unit credit balance output."""
    unit_id: UUID
    credit_balance: Decimal
    last_updated: datetime


class CreditTransactionOut(Schema):
    """Credit transaction history entry."""
    id: UUID
    transaction_type: str
    amount: Decimal
    balance_after: Decimal
    description: str
    created_at: datetime


class FinancialSummaryOut(Schema):
    """Financial summary output."""
    period: str
    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal
    transaction_count: int


class CategoryBreakdownOut(Schema):
    """Category breakdown output."""
    category_id: Optional[UUID]
    category_name: str
    total_amount: Decimal
    transaction_count: int
    percentage: Decimal


class MonthlyTrendOut(Schema):
    """Monthly trend data point."""
    year: int
    month: int
    income: Decimal
    expense: Decimal
    net: Decimal


class ProfitLossOut(Schema):
    """Profit/loss status output."""
    period: str
    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal
    is_profitable: bool
    percentage_recovered: Decimal


class DuesStatementOut(Schema):
    """Dues statement output."""
    id: UUID
    unit_id: UUID
    statement_month: int
    statement_year: int
    base_amount: Decimal
    penalty_amount: Decimal
    discount_amount: Decimal
    net_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    status: str
    due_date: date
    paid_date: Optional[date]


class IncomeResultOut(Schema):
    """Result of recording income."""
    transaction: TransactionOut
    credit_added: Optional[Decimal] = None


class ApprovalResultOut(Schema):
    """Result of approval action."""
    transaction: TransactionOut
    credit_added: Optional[Decimal] = None
    message: str


class ErrorOut(Schema):
    """Error response."""
    detail: str


class SuccessOut(Schema):
    """Success response."""
    success: bool
    message: str = ""
