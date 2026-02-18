"""Services for Assets app - Core business logic."""
from typing import List, Optional, Tuple
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.core.files.uploadedfile import UploadedFile
from apps.ledger.models import (
    Transaction, TransactionType, TransactionStatus, TransactionAttachment
)
from apps.ledger.services import record_income, confirm_transaction
from apps.ledger.attachment_service import upload_receipt
from apps.ledger.models import DiscountConfig

from .models import Asset, Reservation, ReservationStatus, PaymentStatus, ReservationConfig
from .dtos import (
    AssetDTO, AssetAnalyticsDTO, AssetTransactionDTO,
    ReservationDTO, AvailabilitySlotDTO, ReservationBreakdownDTO,
    DiscountPreviewDTO, ReservationConfigDTO,
)
# ... existing imports ...

# ... inside submit_reservation_receipt ...

def submit_reservation_receipt(
    reservation_id: UUID,
    file: UploadedFile,
    uploaded_by_id: UUID,
) -> ReservationDTO:
    """
    Submit a receipt for reservation payment.
    Creates a PENDING transaction, uploads the file, and updates reservation status to FOR_REVIEW.
    """
    reservation = Reservation.objects.get(id=reservation_id)
    asset = Asset.objects.get(id=reservation.asset_id)
    
    if reservation.status not in [ReservationStatus.PENDING_PAYMENT, ReservationStatus.FOR_REVIEW]:
        raise ValueError("Receipt can only be submitted for pending reservations")
        
    # Create PENDING transaction
    # Note: We use the full amount for now, assuming 1 receipt = full payment
    amount_to_pay = reservation.balance_due
    
    income_dto, _ = record_income(
        org_id=reservation.org_id,
        amount=amount_to_pay,
        category="Rental Income",
        description=f"Initial receipt submission for {asset.name} - {reservation.reserved_by_name}",
        transaction_date=timezone.now().date(),
        payment_type='EXACT',
        unit_id=reservation.unit_id,
        payer_name=reservation.reserved_by_name,
        created_by_id=uploaded_by_id,
        status=TransactionStatus.PENDING,
    )
    
    # Upload receipt using attachment service
    # This handles validation and storage (S3/local)
    upload_receipt(
        file=file,
        transaction_id=income_dto.id,
        uploaded_by_id=uploaded_by_id
    )
    
    # Update reservation
    reservation.status = ReservationStatus.FOR_REVIEW
    reservation.income_transaction_id = income_dto.id
    reservation.save()
    
    return _reservation_to_dto(reservation, asset.name)
from .dtos import (
    AssetDTO, AssetAnalyticsDTO, AssetTransactionDTO,
    ReservationDTO, AvailabilitySlotDTO, ReservationBreakdownDTO,
    DiscountPreviewDTO, ReservationConfigDTO,
)

# Default expiration time (used when no ReservationConfig exists)
DEFAULT_EXPIRATION_HOURS = 48


# =============================================================================
# Configuration Services
# =============================================================================

def get_expiration_hours(org_id: UUID) -> int:
    """
    Get the reservation expiration hours for an organization.
    Falls back to DEFAULT_EXPIRATION_HOURS if no config exists.
    """
    try:
        config = ReservationConfig.objects.get(org_id=org_id, is_active=True)
        return config.expiration_hours
    except ReservationConfig.DoesNotExist:
        return DEFAULT_EXPIRATION_HOURS


def get_reservation_config(org_id: UUID) -> Optional[ReservationConfigDTO]:
    """Get reservation configuration for an organization."""
    try:
        config = ReservationConfig.objects.get(org_id=org_id, is_active=True)
        return ReservationConfigDTO(
            id=config.id,
            org_id=config.org_id,
            expiration_hours=config.expiration_hours,
            allow_same_day_booking=config.allow_same_day_booking,
            min_advance_hours=config.min_advance_hours,
            operating_hours_start=str(config.operating_hours_start)[:5],
            operating_hours_end=str(config.operating_hours_end)[:5],
            is_active=config.is_active,
        )
    except ReservationConfig.DoesNotExist:
        return None


def create_or_update_reservation_config(
    org_id: UUID,
    expiration_hours: int = DEFAULT_EXPIRATION_HOURS,
    allow_same_day_booking: bool = True,
    min_advance_hours: int = 0,
    operating_hours_start: str = '09:00',
    operating_hours_end: str = '22:00',
) -> ReservationConfigDTO:
    """Create or update reservation configuration for an organization."""
    config, created = ReservationConfig.objects.update_or_create(
        org_id=org_id,
        defaults={
            'expiration_hours': expiration_hours,
            'allow_same_day_booking': allow_same_day_booking,
            'min_advance_hours': min_advance_hours,
            'operating_hours_start': operating_hours_start,
            'operating_hours_end': operating_hours_end,
            'is_active': True,
        }
    )
    return ReservationConfigDTO(
        id=config.id,
        org_id=config.org_id,
        expiration_hours=config.expiration_hours,
        allow_same_day_booking=config.allow_same_day_booking,
        min_advance_hours=config.min_advance_hours,
        operating_hours_start=str(config.operating_hours_start)[:5],
        operating_hours_end=str(config.operating_hours_end)[:5],
        is_active=config.is_active,
    )


# =============================================================================
# Asset CRUD Services
# =============================================================================

def get_asset_dto(asset_id: UUID) -> Optional[AssetDTO]:
    """Get asset DTO by ID."""
    try:
        asset = Asset.objects.get(id=asset_id)
        return _asset_to_dto(asset)
    except Asset.DoesNotExist:
        return None


def list_assets(
    org_id: UUID,
    include_inactive: bool = False,
    search: Optional[str] = None,
    asset_type: Optional[str] = None,
) -> List[AssetDTO]:
    """
    List all assets for an organization.
    Supports search by name/description and filter by asset_type.
    """
    queryset = Asset.objects.filter(org_id=org_id)
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    
    # Search filter (supports debounced client-side search)
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )
    
    # Asset type filter
    if asset_type:
        queryset = queryset.filter(asset_type=asset_type)
    
    return [_asset_to_dto(a) for a in queryset]


def create_asset(org_id: UUID, data) -> AssetDTO:
    """Create a new asset."""
    asset = Asset.objects.create(
        org_id=org_id,
        name=data.name,
        asset_type=data.asset_type,
        description=data.description,
        image_url=data.image_url,
        rental_rate=data.rental_rate,
        capacity=data.capacity,
        location=data.location,
        requires_deposit=data.requires_deposit,
        deposit_amount=data.deposit_amount,
        min_duration_hours=data.min_duration_hours,
        max_duration_hours=data.max_duration_hours,
    )
    return _asset_to_dto(asset)


def update_asset(asset_id: UUID, data) -> Optional[AssetDTO]:
    """Update an existing asset."""
    try:
        asset = Asset.objects.get(id=asset_id)
        for field in ['name', 'asset_type', 'description', 'image_url', 'rental_rate', 
                      'capacity', 'location', 'requires_deposit', 'deposit_amount',
                      'min_duration_hours', 'max_duration_hours']:
            if hasattr(data, field):
                setattr(asset, field, getattr(data, field))
        asset.save()
        return _asset_to_dto(asset)
    except Asset.DoesNotExist:
        return None


def soft_delete_asset(asset_id: UUID) -> bool:
    """Soft delete an asset."""
    try:
        asset = Asset.objects.get(id=asset_id)
        asset.is_active = False
        asset.save()
        return True
    except Asset.DoesNotExist:
        return False


def bulk_delete_assets(asset_ids: List[UUID]) -> int:
    """
    Bulk soft-delete assets.
    Returns count of deleted assets.
    """
    count = Asset.objects.filter(id__in=asset_ids).update(is_active=False)
    return count


# =============================================================================
# Asset Analytics Services (User Stories #1, #2, #3)
# =============================================================================

def get_assets_with_analytics(org_id: UUID) -> List[AssetAnalyticsDTO]:
    """
    Get all assets with current month's income/expense summary.
    User Story #1: See list of shared infrastructures and monthly income.
    """
    assets = Asset.objects.filter(org_id=org_id, is_active=True)
    
    # Current month range
    today = timezone.now().date()
    month_start = date(today.year, today.month, 1)
    if today.month == 12:
        month_end = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(today.year, today.month + 1, 1) - timedelta(days=1)
    
    results = []
    for asset in assets:
        # Get income from Ledger transactions
        income = Transaction.objects.filter(
            asset_id=asset.id,
            transaction_type=TransactionType.INCOME,
            status=TransactionStatus.POSTED,
            transaction_date__gte=month_start,
            transaction_date__lte=month_end,
        ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')
        
        # Get expenses from Ledger transactions
        expenses = Transaction.objects.filter(
            asset_id=asset.id,
            transaction_type=TransactionType.EXPENSE,
            status=TransactionStatus.POSTED,
            transaction_date__gte=month_start,
            transaction_date__lte=month_end,
        ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')
        
        # Count reservations this month
        reservation_count = Reservation.objects.filter(
            asset_id=asset.id,
            status__in=[ReservationStatus.CONFIRMED, ReservationStatus.COMPLETED],
            start_datetime__date__gte=month_start,
            start_datetime__date__lte=month_end,
        ).count()
        
        results.append(AssetAnalyticsDTO(
            asset_id=asset.id,
            asset_name=asset.name,
            asset_type=asset.asset_type,
            image_url=asset.image_url,
            capacity=asset.capacity,
            rental_rate=asset.rental_rate,
            income_this_month=income,
            expenses_this_month=expenses,
            net_income_this_month=income - expenses,
            reservation_count_this_month=reservation_count,
        ))
    
    return results


def get_asset_transactions(
    asset_id: UUID,
    transaction_type: Optional[str] = None,  # 'INCOME' or 'EXPENSE'
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
) -> List[AssetTransactionDTO]:
    """
    Get transaction history for an asset.
    User Story #2: Drill down to see rent history (income).
    User Story #3: Drill down to see expense history.
    """
    queryset = Transaction.objects.filter(asset_id=asset_id)
    
    if transaction_type:
        queryset = queryset.filter(transaction_type=transaction_type)
    if start_date:
        queryset = queryset.filter(transaction_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(transaction_date__lte=end_date)
    
    transactions = queryset[:limit]
    
    # Get linked reservation IDs if any
    return [
        AssetTransactionDTO(
            id=t.id,
            transaction_type=t.transaction_type,
            amount=t.net_amount,
            category=t.category,
            description=t.description,
            payment_method=t.payment_method,
            transaction_date=t.transaction_date,
            reservation_id=_get_reservation_for_transaction(t.id),
            created_at=t.created_at,
        )
        for t in transactions
    ]


# =============================================================================
# Availability Services (User Story #4)
# =============================================================================

def get_asset_availability(
    asset_id: UUID,
    start_date: date,
    end_date: date,
) -> List[AvailabilitySlotDTO]:
    """
    Get availability schedule for an asset.
    User Story #4: View infrastructure availability.
    Returns booked slots (not available).
    """
    # Get all active reservations in the date range
    reservations = Reservation.objects.filter(
        asset_id=asset_id,
        status__in=[
            ReservationStatus.PENDING_PAYMENT,
            ReservationStatus.CONFIRMED,
        ],
        start_datetime__date__lte=end_date,
        end_datetime__date__gte=start_date,
    ).order_by('start_datetime')
    
    slots = []
    for res in reservations:
        slots.append(AvailabilitySlotDTO(
            start_datetime=res.start_datetime,
            end_datetime=res.end_datetime,
            is_available=False,
            reservation_id=res.id,
            reserved_by_name=res.reserved_by_name,
        ))
    
    return slots


def check_slot_available(
    asset_id: UUID,
    start_datetime: datetime,
    end_datetime: datetime,
    exclude_reservation_id: Optional[UUID] = None,
) -> bool:
    """Check if a specific timeslot is available."""
    queryset = Reservation.objects.filter(
        asset_id=asset_id,
        status__in=[
            ReservationStatus.PENDING_PAYMENT,
            ReservationStatus.CONFIRMED,
        ],
    ).filter(
        # Overlapping check
        Q(start_datetime__lt=end_datetime) & Q(end_datetime__gt=start_datetime)
    )
    
    if exclude_reservation_id:
        queryset = queryset.exclude(id=exclude_reservation_id)
    
    return not queryset.exists()


# =============================================================================
# Reservation Services (User Stories #5, #8, #9)
# =============================================================================

def create_reservation(
    org_id: UUID,
    data,
    created_by_id: UUID,
    is_homeowner: bool = False,
) -> ReservationDTO:
    """
    Create a reservation.
    User Story #5: Pick timeslot to reserve.
    User Story #8: Homeowners get PENDING_PAYMENT status with expiration.
    """
    asset = Asset.objects.get(id=data.asset_id)
    
    # Check availability
    if not check_slot_available(data.asset_id, data.start_datetime, data.end_datetime):
        raise ValueError("Selected timeslot is not available")
    
    # Calculate hours and pricing
    duration = data.end_datetime - data.start_datetime
    hours = int(duration.total_seconds() / 3600)
    
    # Validate duration
    if hours < asset.min_duration_hours:
        raise ValueError(f"Minimum reservation is {asset.min_duration_hours} hours")
    if hours > asset.max_duration_hours:
        raise ValueError(f"Maximum reservation is {asset.max_duration_hours} hours")
    
    hourly_rate = asset.rental_rate or Decimal('0.00')
    subtotal = hourly_rate * hours
    
    # Calculate discounts
    discount_amount = Decimal('0.00')
    applied_ids = []
    if data.apply_discount_ids:
        for discount_id in data.apply_discount_ids:
            try:
                discount = DiscountConfig.objects.get(id=discount_id, is_active=True)
                if discount.discount_type == 'PERCENTAGE':
                    discount_amount += (subtotal * discount.value / 100).quantize(Decimal('0.01'))
                else:
                    discount_amount += discount.value
                applied_ids.append(str(discount_id))
            except DiscountConfig.DoesNotExist:
                pass
    
    # Deposit
    deposit_amount = asset.deposit_amount if asset.requires_deposit else Decimal('0.00')
    
    # Total
    total_amount = subtotal - discount_amount + (deposit_amount or Decimal('0.00'))
    
    # Determine status and expiration
    if is_homeowner:
        status = ReservationStatus.PENDING_PAYMENT
        expiration_hours = get_expiration_hours(org_id)
        if expiration_hours > 0:
            expires_at = timezone.now() + timedelta(hours=expiration_hours)
        else:
            expires_at = None  # 0 means no expiration
    else:
        status = ReservationStatus.CONFIRMED
        expires_at = None
    
    reservation = Reservation.objects.create(
        org_id=org_id,
        asset_id=data.asset_id,
        unit_id=data.unit_id,
        reserved_by_id=created_by_id,
        reserved_by_name=data.reserved_by_name,
        contact_phone=data.contact_phone,
        contact_email=data.contact_email,
        purpose=data.purpose,
        start_datetime=data.start_datetime,
        end_datetime=data.end_datetime,
        hourly_rate=hourly_rate,
        hours=hours,
        subtotal=subtotal,
        discount_amount=discount_amount,
        deposit_amount=deposit_amount or Decimal('0.00'),
        total_amount=total_amount,
        status=status,
        expires_at=expires_at,
        applied_discount_ids=applied_ids,
    )
    
    return _reservation_to_dto(reservation, asset.name)


def get_reservation(reservation_id: UUID) -> Optional[ReservationDTO]:
    """Get a reservation by ID."""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
        asset = Asset.objects.get(id=reservation.asset_id)
        return _reservation_to_dto(reservation, asset.name)
    except (Reservation.DoesNotExist, Asset.DoesNotExist):
        return None


def list_reservations(
    org_id: UUID,
    asset_id: Optional[UUID] = None,
    reserved_by_id: Optional[UUID] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
) -> List[ReservationDTO]:
    """List reservations with filtering."""
    queryset = Reservation.objects.filter(org_id=org_id)
    
    if asset_id:
        queryset = queryset.filter(asset_id=asset_id)
    if reserved_by_id:
        queryset = queryset.filter(reserved_by_id=reserved_by_id)
    if status:
        queryset = queryset.filter(status=status)
    if start_date:
        queryset = queryset.filter(start_datetime__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(start_datetime__date__lte=end_date)
    
    reservations = queryset[:limit]
    
    # Build asset name lookup
    asset_ids = set(r.asset_id for r in reservations)
    assets = {a.id: a.name for a in Asset.objects.filter(id__in=asset_ids)}
    
    return [
        _reservation_to_dto(r, assets.get(r.asset_id, "Unknown"))
        for r in reservations
    ]


def record_reservation_payment(
    reservation_id: UUID,
    amount: Decimal,
    recorded_by_id: UUID,
    reference_number: Optional[str] = None,
) -> ReservationDTO:
    """
    Record payment for a reservation.
    Confirms the reservation if fully paid.
    Creates income transaction via Ledger (which also creates TransactionAdjustment records).
    """
    reservation = Reservation.objects.get(id=reservation_id)
    asset = Asset.objects.get(id=reservation.asset_id)
    
    if reservation.status in [ReservationStatus.CANCELLED, ReservationStatus.EXPIRED]:
        raise ValueError("Cannot record payment for cancelled/expired reservation")
    
    reservation.amount_paid += amount
    
    # Update payment status
    if reservation.amount_paid >= reservation.total_amount:
        reservation.payment_status = PaymentStatus.PAID
        reservation.status = ReservationStatus.CONFIRMED
        reservation.expires_at = None  # No longer needs to expire
    elif reservation.amount_paid > Decimal('0.00'):
        reservation.payment_status = PaymentStatus.PARTIAL
    
    reservation.save()
    
    # Record income in Ledger (with asset_id linkage)
    # This creates the Transaction and any TransactionAdjustment records
    income_dto, _ = record_income(
        org_id=reservation.org_id,
        amount=amount,
        category="Rental Income",
        description=f"Rental payment for {asset.name} - {reservation.reserved_by_name}",
        transaction_date=timezone.now().date(),
        payment_type='EXACT',
        unit_id=reservation.unit_id,
        payer_name=reservation.reserved_by_name,
        reference_number=reference_number,
        created_by_id=recorded_by_id,
    )
    
    # Link transaction to reservation (for breakdown retrieval)
    if not reservation.income_transaction_id:
        reservation.income_transaction_id = income_dto.id
        reservation.save()
    
    return _reservation_to_dto(reservation, asset.name)


def submit_reservation_receipt(
    reservation_id: UUID,
    file_url: str,
    file_name: str,
    file_type: str,
    file_size: int,
    uploaded_by_id: UUID,
) -> ReservationDTO:
    """
    Submit a receipt for reservation payment.
    Creates a PENDING transaction and updates reservation status to FOR_REVIEW.
    """
    reservation = Reservation.objects.get(id=reservation_id)
    asset = Asset.objects.get(id=reservation.asset_id)
    
    if reservation.status not in [ReservationStatus.PENDING_PAYMENT, ReservationStatus.FOR_REVIEW]:
        raise ValueError("Receipt can only be submitted for pending reservations")
        
    # Create PENDING transaction
    # Note: We use the full amount for now, assuming 1 receipt = full payment
    # If the user uploads partial payment receipt, staff can adjust or reject?
    # For MVP, we assume it covers the balance due.
    amount_to_pay = reservation.balance_due
    
    income_dto, _ = record_income(
        org_id=reservation.org_id,
        amount=amount_to_pay,
        category="Rental Income",
        description=f"Initial receipt submission for {asset.name} - {reservation.reserved_by_name}",
        transaction_date=timezone.now().date(),
        payment_type='EXACT',
        unit_id=reservation.unit_id,
        payer_name=reservation.reserved_by_name,
        created_by_id=uploaded_by_id,
        status=TransactionStatus.PENDING,
    )
    
    # Create attachment for the transaction
    TransactionAttachment.objects.create(
        transaction_id=income_dto.id,
        file_url=file_url,
        file_name=file_name,
        file_type=file_type,
        file_size=file_size,
        uploaded_by_id=uploaded_by_id,
    )
    
    # Update reservation
    reservation.status = ReservationStatus.FOR_REVIEW
    reservation.income_transaction_id = income_dto.id
    reservation.save()
    
    return _reservation_to_dto(reservation, asset.name)


def confirm_reservation_receipt(
    reservation_id: UUID,
    confirmed_by_id: UUID,
) -> ReservationDTO:
    """
    Confirm a reservation receipt.
    Verifies the pending transaction (posts it) and confirms the reservation.
    """
    reservation = Reservation.objects.get(id=reservation_id)
    asset = Asset.objects.get(id=reservation.asset_id)
    
    if reservation.status != ReservationStatus.FOR_REVIEW:
        raise ValueError("Only reservations 'For Review' can be confirmed")
    
    if not reservation.income_transaction_id:
        raise ValueError("No transaction linked to this reservation")
        
    # Confirm transaction (this posts it to ledger)
    transaction_dto = confirm_transaction(
        transaction_id=reservation.income_transaction_id,
        verified_by_id=confirmed_by_id,
    )
    
    # Update reservation payment tracking
    reservation.amount_paid += transaction_dto.amount
    
    if reservation.amount_paid >= reservation.total_amount:
        reservation.payment_status = PaymentStatus.PAID
        reservation.status = ReservationStatus.CONFIRMED
        reservation.expires_at = None
    elif reservation.amount_paid > Decimal('0.00'):
        # This shouldn't normally happen if we created transaction for full balance
        reservation.payment_status = PaymentStatus.PARTIAL
        reservation.status = ReservationStatus.CONFIRMED # Still confirm if partially paid? Or back to PENDING_PAYMENT?
        # Requirement says "change the status to confirmed after viewing".
        # We'll assume confirmation means "Accept Payment & Confirm Reservation"
        reservation.expires_at = None
        
    reservation.approved_by_id = confirmed_by_id
    reservation.approved_at = timezone.now()
    reservation.save()
    
    return _reservation_to_dto(reservation, asset.name)


def cancel_reservation(
    reservation_id: UUID,
    cancelled_by_id: UUID,
    reason: str = "",
) -> ReservationDTO:
    """Cancel a reservation."""
    reservation = Reservation.objects.get(id=reservation_id)
    asset = Asset.objects.get(id=reservation.asset_id)
    
    if reservation.status in [ReservationStatus.CANCELLED, ReservationStatus.EXPIRED, ReservationStatus.COMPLETED]:
        raise ValueError(f"Cannot cancel reservation with status {reservation.status}")
    
    reservation.status = ReservationStatus.CANCELLED
    reservation.cancelled_by_id = cancelled_by_id
    reservation.cancelled_at = timezone.now()
    reservation.cancellation_reason = reason
    reservation.save()
    
    return _reservation_to_dto(reservation, asset.name)


def expire_unpaid_reservations() -> int:
    """
    Expire all reservations past their expires_at datetime.
    User Story #9: Auto-expire unpaid reservations.
    Returns count of expired reservations.
    """
    now = timezone.now()
    expired = Reservation.objects.filter(
        status=ReservationStatus.PENDING_PAYMENT,
        expires_at__lt=now,
    ).update(status=ReservationStatus.EXPIRED)
    
    return expired


# =============================================================================
# Payment Preview Services (User Stories #6, #7)
# =============================================================================

def get_applicable_discounts(org_id: UUID) -> List[DiscountPreviewDTO]:
    """
    Get currently applicable discounts for reservations.
    User Story #6: Know available discounts before payment.
    """
    today = timezone.now().date()
    
    discounts = DiscountConfig.objects.filter(
        org_id=org_id,
        is_active=True,
    ).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=today),
        Q(valid_until__isnull=True) | Q(valid_until__gte=today),
    )
    
    return [
        DiscountPreviewDTO(
            id=d.id,
            name=d.name,
            discount_type=d.discount_type,
            value=d.value,
            calculated_amount=Decimal('0.00'),  # Calculated when applied to specific amount
        )
        for d in discounts
    ]


def preview_reservation_breakdown(
    asset_id: UUID,
    start_datetime: datetime,
    end_datetime: datetime,
    apply_discount_ids: Optional[List[UUID]] = None,
) -> ReservationBreakdownDTO:
    """
    Get payment breakdown before creating reservation.
    User Story #7: See breakdown before paying.
    """
    asset = Asset.objects.get(id=asset_id)
    
    # Calculate hours
    duration = end_datetime - start_datetime
    hours = int(duration.total_seconds() / 3600)
    
    hourly_rate = asset.rental_rate or Decimal('0.00')
    subtotal = hourly_rate * hours
    
    # Get all applicable discounts
    applicable_discounts = []
    selected_discount_amount = Decimal('0.00')
    
    today = timezone.now().date()
    discounts = DiscountConfig.objects.filter(
        org_id=asset.org_id,
        is_active=True,
    ).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=today),
        Q(valid_until__isnull=True) | Q(valid_until__gte=today),
    )
    
    for discount in discounts:
        if discount.discount_type == 'PERCENTAGE':
            calc_amount = (subtotal * discount.value / 100).quantize(Decimal('0.01'))
        else:
            calc_amount = discount.value
        
        preview = DiscountPreviewDTO(
            id=discount.id,
            name=discount.name,
            discount_type=discount.discount_type,
            value=discount.value,
            calculated_amount=calc_amount,
        )
        applicable_discounts.append(preview)
        
        # If selected, add to total discount
        if apply_discount_ids and discount.id in apply_discount_ids:
            selected_discount_amount += calc_amount
    
    # Deposit
    deposit_required = asset.deposit_amount if asset.requires_deposit else Decimal('0.00')
    
    # Total
    total_amount = subtotal - selected_discount_amount + (deposit_required or Decimal('0.00'))
    
    return ReservationBreakdownDTO(
        hourly_rate=hourly_rate,
        hours=hours,
        subtotal=subtotal,
        applicable_discounts=applicable_discounts,
        selected_discount_amount=selected_discount_amount,
        deposit_required=deposit_required or Decimal('0.00'),
        total_amount=total_amount,
    )


# =============================================================================
# Helper Functions
# =============================================================================

def _asset_to_dto(asset: Asset) -> AssetDTO:
    """Convert Asset model to DTO."""
    return AssetDTO(
        id=asset.id,
        org_id=asset.org_id,
        name=asset.name,
        asset_type=asset.asset_type,
        description=asset.description,
        image_url=asset.image_url,
        rental_rate=asset.rental_rate,
        capacity=asset.capacity,
        location=asset.location,
        requires_deposit=asset.requires_deposit,
        deposit_amount=asset.deposit_amount,
        min_duration_hours=asset.min_duration_hours,
        max_duration_hours=asset.max_duration_hours,
        is_active=asset.is_active,
    )


def _reservation_to_dto(reservation: Reservation, asset_name: str) -> ReservationDTO:
    """Convert Reservation model to DTO."""
    return ReservationDTO(
        id=reservation.id,
        asset_id=reservation.asset_id,
        asset_name=asset_name,
        unit_id=reservation.unit_id,
        reserved_by_id=reservation.reserved_by_id,
        reserved_by_name=reservation.reserved_by_name,
        start_datetime=reservation.start_datetime,
        end_datetime=reservation.end_datetime,
        hourly_rate=reservation.hourly_rate,
        hours=reservation.hours,
        subtotal=reservation.subtotal,
        discount_amount=reservation.discount_amount,
        deposit_amount=reservation.deposit_amount,
        total_amount=reservation.total_amount,
        amount_paid=reservation.amount_paid,
        balance_due=reservation.balance_due,
        status=reservation.status,
        payment_status=reservation.payment_status,
        income_transaction_id=reservation.income_transaction_id,
        expires_at=reservation.expires_at,
        created_at=reservation.created_at,
    )


def _get_reservation_for_transaction(transaction_id: UUID) -> Optional[UUID]:
    """Find reservation linked to a transaction."""
    reservation = Reservation.objects.filter(
        income_transaction_id=transaction_id
    ).first()
    return reservation.id if reservation else None
