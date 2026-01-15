"""API Schemas for Assets app - Pydantic/Ninja schemas for request/response validation."""
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date
from ninja import Schema


# =============================================================================
# Request Schemas
# =============================================================================

class AssetIn(Schema):
    """Schema for creating/updating an asset."""
    name: str
    asset_type: str = 'REVENUE'
    description: str = ""
    rental_rate: Optional[Decimal] = None
    capacity: Optional[int] = None
    location: str = ""
    requires_deposit: bool = False
    deposit_amount: Optional[Decimal] = None
    min_duration_hours: int = 1
    max_duration_hours: int = 24


class ReservationIn(Schema):
    """Schema for creating a reservation."""
    asset_id: UUID
    unit_id: Optional[UUID] = None  # Required for homeowners
    start_datetime: datetime  # ISO 8601 format
    end_datetime: datetime    # ISO 8601 format
    reserved_by_name: str
    contact_phone: str = ""
    contact_email: str = ""
    purpose: str = ""
    apply_discount_ids: Optional[List[UUID]] = None


class ReservationPreviewIn(Schema):
    """Schema for previewing reservation breakdown."""
    asset_id: UUID
    start_datetime: datetime
    end_datetime: datetime
    apply_discount_ids: Optional[List[UUID]] = None


class ReservationPaymentIn(Schema):
    """Schema for recording payment."""
    amount: Decimal
    reference_number: Optional[str] = None
    payment_method: str = "CASH"  # CASH, BANK_TRANSFER, GCASH, etc.


class CancellationIn(Schema):
    """Schema for cancellation."""
    reason: str = ""


class ReservationConfigIn(Schema):
    """Schema for updating reservation configuration."""
    expiration_hours: int = 48
    allow_same_day_booking: bool = True
    min_advance_hours: int = 0


# =============================================================================
# Response Schemas
# =============================================================================

class AssetOut(Schema):
    """Basic asset output."""
    id: UUID
    name: str
    asset_type: str
    description: str
    rental_rate: Optional[Decimal]
    capacity: Optional[int]
    location: str
    requires_deposit: bool
    deposit_amount: Optional[Decimal]
    min_duration_hours: int
    max_duration_hours: int
    is_active: bool


class AssetWithAnalyticsOut(Schema):
    """Asset with current month's income/expense summary."""
    id: UUID
    name: str
    asset_type: str
    rental_rate: Optional[Decimal]
    income_this_month: Decimal
    expenses_this_month: Decimal
    net_income_this_month: Decimal
    reservation_count_this_month: int


class AssetTransactionOut(Schema):
    """Transaction linked to an asset (income or expense)."""
    id: UUID
    transaction_type: str
    amount: Decimal
    category: str
    description: str
    transaction_date: date
    reservation_id: Optional[UUID]
    created_at: datetime  # ISO 8601


class ReservationOut(Schema):
    """Reservation output with full breakdown."""
    id: UUID
    asset_id: UUID
    asset_name: str
    unit_id: Optional[UUID]
    reserved_by_id: UUID
    reserved_by_name: str
    start_datetime: datetime  # ISO 8601
    end_datetime: datetime    # ISO 8601
    hourly_rate: Decimal
    hours: int
    subtotal: Decimal
    discount_amount: Decimal
    deposit_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    status: str
    payment_status: str
    income_transaction_id: Optional[UUID]  # For retrieving Ledger breakdown
    expires_at: Optional[datetime]  # ISO 8601
    created_at: datetime  # ISO 8601


class AvailabilitySlotOut(Schema):
    """Time slot availability."""
    start_datetime: datetime
    end_datetime: datetime
    is_available: bool
    reservation_id: Optional[UUID] = None
    reserved_by_name: Optional[str] = None


class DiscountPreviewOut(Schema):
    """Applicable discount preview."""
    id: UUID
    name: str
    discount_type: str
    value: Decimal
    calculated_amount: Decimal


class ReservationBreakdownOut(Schema):
    """Payment breakdown preview (same structure as dues breakdown)."""
    hourly_rate: Decimal
    hours: int
    subtotal: Decimal
    applicable_discounts: List[DiscountPreviewOut]
    selected_discount_amount: Decimal
    deposit_required: Decimal
    total_amount: Decimal


class ReservationConfigOut(Schema):
    """Reservation configuration output."""
    id: UUID
    org_id: UUID
    expiration_hours: int
    allow_same_day_booking: bool
    min_advance_hours: int
    is_active: bool


class ErrorOut(Schema):
    """Error response."""
    detail: str


class SuccessOut(Schema):
    """Success response."""
    message: str
