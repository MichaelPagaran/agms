"""Models for Assets app."""
import uuid
from decimal import Decimal
from django.db import models


class AssetType(models.TextChoices):
    REVENUE = 'REVENUE', 'Revenue-Generating'
    SHARED = 'SHARED', 'Shared Infrastructure'


class Asset(models.Model):
    """
    Represents facilities (Pool, Clubhouse, Gates, etc.).
    Revenue facilities have rental rates; shared don't.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    
    name = models.CharField(max_length=255)
    asset_type = models.CharField(
        max_length=20,
        choices=AssetType.choices,
        default=AssetType.SHARED
    )
    description = models.TextField(blank=True)
    rental_rate = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Rental rate per hour (for revenue facilities)"
    )
    
    # Additional fields for reservations
    capacity = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Maximum capacity (number of people)"
    )
    location = models.CharField(
        max_length=255, blank=True,
        help_text="Physical location within the subdivision/building"
    )
    requires_deposit = models.BooleanField(default=False)
    deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Security deposit amount"
    )
    min_duration_hours = models.PositiveIntegerField(
        default=1,
        help_text="Minimum reservation duration in hours"
    )
    max_duration_hours = models.PositiveIntegerField(
        default=24,
        help_text="Maximum reservation duration in hours"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ReservationConfig(models.Model):
    """
    Organization-level reservation policies.
    Allows STAFF/BOARD to configure expiration time and other settings.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(unique=True, db_index=True)
    
    expiration_hours = models.PositiveIntegerField(
        default=48,
        help_text="Hours until unpaid homeowner reservation expires (0 = no expiration)"
    )
    
    # Future expansion: cancellation policy, deposit policy, etc.
    allow_same_day_booking = models.BooleanField(
        default=True,
        help_text="Allow reservations for today"
    )
    min_advance_hours = models.PositiveIntegerField(
        default=0,
        help_text="Minimum hours in advance to book (0 = no limit)"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Reservation Configuration"
        verbose_name_plural = "Reservation Configurations"
    
    def __str__(self):
        return f"Reservation Config - Org {self.org_id}"


class ReservationStatus(models.TextChoices):
    PENDING_PAYMENT = 'PENDING_PAYMENT', 'Pending Payment'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    EXPIRED = 'EXPIRED', 'Expired'


class PaymentStatus(models.TextChoices):
    UNPAID = 'UNPAID', 'Unpaid'
    PARTIAL = 'PARTIAL', 'Partially Paid'
    PAID = 'PAID', 'Paid'
    REFUNDED = 'REFUNDED', 'Refunded'


class Reservation(models.Model):
    """
    Infrastructure reservation/booking.
    Tracks scheduling, pricing, and payment status.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    asset_id = models.UUIDField(db_index=True)  # References Asset
    unit_id = models.UUIDField(null=True, blank=True, db_index=True)  # References Unit (for homeowners)
    
    # Booking details
    reserved_by_id = models.UUIDField(db_index=True)  # References User
    reserved_by_name = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    purpose = models.TextField(blank=True)
    
    # Schedule (ISO 8601 compatible datetimes)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    
    # Pricing breakdown (persisted for historical reference)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    hours = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)  # hourly_rate × hours
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PENDING_PAYMENT
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID
    )
    
    # Linked income transaction (created when payment is recorded)
    # Used to retrieve TransactionAdjustment breakdown from Ledger
    income_transaction_id = models.UUIDField(null=True, blank=True)
    
    # Applied discounts (JSON list of discount IDs for reference)
    applied_discount_ids = models.JSONField(default=list, blank=True)
    
    # Workflow
    approved_by_id = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by_id = models.UUIDField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    # Expiration (for unpaid homeowner reservations)
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When unpaid reservation expires (null for staff/board reservations)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_datetime']
        indexes = [
            models.Index(fields=['org_id', 'asset_id', 'status']),
            models.Index(fields=['org_id', 'reserved_by_id']),
            models.Index(fields=['expires_at']),  # For expiration task
        ]

    def __str__(self):
        return f"Reservation {self.id} - {self.reserved_by_name}"
    
    @property
    def balance_due(self) -> Decimal:
        """Returns remaining balance to be paid."""
        return self.total_amount - self.amount_paid
