"""DTOs for Assets app - Data Transfer Objects for cross-app communication."""
from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date


@dataclass(frozen=True)
class AssetDTO:
    """Basic asset data for cross-app communication."""
    id: UUID
    org_id: UUID
    name: str
    asset_type: str
    description: str
    image_url: Optional[str]
    rental_rate: Optional[Decimal]
    capacity: Optional[int]
    location: str
    requires_deposit: bool
    deposit_amount: Optional[Decimal]
    min_duration_hours: int
    max_duration_hours: int
    is_active: bool


@dataclass(frozen=True)
class AssetAnalyticsDTO:
    """Asset with current month's financial summary."""
    asset_id: UUID
    asset_name: str
    asset_type: str
    image_url: Optional[str]
    capacity: Optional[int]
    rental_rate: Optional[Decimal]
    income_this_month: Decimal
    expenses_this_month: Decimal
    net_income_this_month: Decimal
    reservation_count_this_month: int


@dataclass(frozen=True)
class AssetTransactionDTO:
    """Transaction linked to an asset (from Ledger)."""
    id: UUID
    transaction_type: str  # 'INCOME' or 'EXPENSE'
    amount: Decimal
    category: str
    description: str
    transaction_date: date
    reservation_id: Optional[UUID]  # For rental income
    created_at: datetime


@dataclass(frozen=True)
class ReservationDTO:
    """Reservation data."""
    id: UUID
    asset_id: UUID
    asset_name: str
    unit_id: Optional[UUID]
    reserved_by_id: UUID
    reserved_by_name: str
    start_datetime: datetime
    end_datetime: datetime
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
    income_transaction_id: Optional[UUID]
    expires_at: Optional[datetime]
    created_at: datetime


@dataclass(frozen=True)
class AvailabilitySlotDTO:
    """Time slot availability info."""
    start_datetime: datetime
    end_datetime: datetime
    is_available: bool
    reservation_id: Optional[UUID] = None  # If booked, who reserved it
    reserved_by_name: Optional[str] = None


@dataclass(frozen=True)
class DiscountPreviewDTO:
    """Preview of an applicable discount."""
    id: UUID
    name: str
    discount_type: str
    value: Decimal
    calculated_amount: Decimal


@dataclass(frozen=True)
class ReservationBreakdownDTO:
    """
    Payment breakdown before reservation submission.
    Same structure as monthly dues breakdown for consistent UX.
    """
    hourly_rate: Decimal
    hours: int
    subtotal: Decimal  # hourly_rate × hours
    applicable_discounts: List[DiscountPreviewDTO]
    selected_discount_amount: Decimal  # Sum of selected discounts
    deposit_required: Decimal
    total_amount: Decimal  # subtotal - discount + deposit


@dataclass(frozen=True)
class ReservationConfigDTO:
    """Reservation configuration for an organization."""
    id: UUID
    org_id: UUID
    expiration_hours: int
    allow_same_day_booking: bool
    min_advance_hours: int
    is_active: bool
