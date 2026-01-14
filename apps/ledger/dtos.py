"""DTOs for Ledger app - Data Transfer Objects for cross-app communication."""
from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import date, datetime


@dataclass(frozen=True)
class TransactionDTO:
    """Basic transaction data for cross-app communication."""
    id: UUID
    org_id: UUID
    transaction_type: str
    status: str
    amount: Decimal
    net_amount: Decimal
    category: str
    category: str
    transaction_date: date
    is_verified: bool = False


@dataclass(frozen=True)
class TransactionDetailDTO:
    """Detailed transaction data including all fields."""
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
    verified_by_id: Optional[UUID]
    verified_at: Optional[datetime]
    created_at: datetime
    is_verified: bool = False


@dataclass(frozen=True)
class TransactionCategoryDTO:
    """Transaction category data."""
    id: UUID
    name: str
    transaction_type: str
    description: str
    is_active: bool


@dataclass(frozen=True)
class AdjustmentPreviewDTO:
    """Preview of an adjustment to be applied."""
    adjustment_type: str  # 'DISCOUNT' or 'PENALTY'
    amount: Decimal
    reason: str
    months_overdue: Optional[int] = None  # For penalties


@dataclass(frozen=True)
class DiscountPreviewDTO:
    """Preview of an applicable discount."""
    id: UUID
    name: str
    discount_type: str
    value: Decimal
    calculated_amount: Decimal  # Actual discount amount for this transaction


@dataclass(frozen=True)
class PenaltyPreviewDTO:
    """Preview of a pending penalty."""
    name: str
    principal: Decimal
    rate: Decimal
    months_overdue: int
    calculated_amount: Decimal  # Result of simple interest calculation


@dataclass(frozen=True)
class TransactionBreakdownDTO:
    """
    Complete breakdown of a transaction before submission.
    Shows gross amount, all adjustments, and final net amount.
    """
    gross_amount: Decimal
    adjustments: List[AdjustmentPreviewDTO]
    pending_penalties: List[PenaltyPreviewDTO]
    applicable_discounts: List[DiscountPreviewDTO]
    net_amount: Decimal
    credit_to_add: Optional[Decimal] = None  # For advance payments


@dataclass(frozen=True)
class DuesStatementDTO:
    """Monthly dues statement data."""
    id: UUID
    org_id: UUID
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


@dataclass(frozen=True)
class UnitCreditDTO:
    """Unit credit balance data."""
    unit_id: UUID
    credit_balance: Decimal
    last_updated: datetime


@dataclass(frozen=True)
class CreditTransactionDTO:
    """Credit transaction history entry."""
    id: UUID
    transaction_type: str
    amount: Decimal
    balance_after: Decimal
    description: str
    created_at: datetime


@dataclass(frozen=True)
class ValidationResultDTO:
    """Result of transaction validation."""
    valid: bool
    error: Optional[str] = None
    credit_to_add: Optional[Decimal] = None


@dataclass(frozen=True)
class FinancialSummaryDTO:
    """Financial summary for dashboards (MTD/YTD)."""
    period: str  # 'MTD' or 'YTD'
    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal
    transaction_count: int


@dataclass(frozen=True)
class CategoryBreakdownDTO:
    """Expense or income broken down by category."""
    category_id: UUID
    category_name: str
    total_amount: Decimal
    transaction_count: int
    percentage: Decimal  # Percentage of total


@dataclass(frozen=True)
class MonthlyTrendDTO:
    """Monthly trend data point."""
    year: int
    month: int
    income: Decimal
    expense: Decimal
    net: Decimal


@dataclass(frozen=True)
class ProfitLossStatusDTO:
    """Current profit/loss status."""
    period: str
    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal
    is_profitable: bool
    percentage_recovered: Decimal  # % of expenses covered by income
