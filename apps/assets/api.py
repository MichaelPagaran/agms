"""API Router for Assets app."""
from typing import List, Optional
from uuid import UUID
from datetime import date
from ninja import Router, File
from ninja.errors import HttpError
from ninja.files import UploadedFile
from django.http import HttpRequest

from apps.identity.permissions import Permissions, get_user_permissions
from apps.identity.models import UserRole

from . import services
from .schemas import (
    AssetIn, AssetOut, AssetWithAnalyticsOut, AssetTransactionOut,
    ReservationIn, ReservationOut, ReservationPreviewIn, ReservationBreakdownOut,
    ReservationPaymentIn, CancellationIn, AvailabilitySlotOut, DiscountPreviewOut,
    ReservationConfigIn, ReservationConfigOut, BulkDeleteIn,
)

router = Router(tags=["Assets"])


# =============================================================================
# Helper Functions
# =============================================================================

def require_auth(request: HttpRequest):
    """Require authenticated user."""
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")


def require_permission(request: HttpRequest, permission: str):
    """Require specific permission."""
    require_auth(request)
    perms = get_user_permissions(request.user)
    if permission not in perms:
        raise HttpError(403, f"Permission denied: {permission}")


def get_org_id(request: HttpRequest) -> UUID:
    """Get organization ID from user."""
    if not request.user.org_id_id:
        raise HttpError(400, "User has no organization context")
    return request.user.org_id_id


def is_homeowner(request: HttpRequest) -> bool:
    """Check if user is homeowner."""
    return request.user.role == UserRole.HOMEOWNER


# =============================================================================
# Asset CRUD Endpoints
# =============================================================================

@router.get("/", response=List[AssetOut], auth=None)
def list_assets(
    request: HttpRequest,
    search: Optional[str] = None,
    asset_type: Optional[str] = None,
):
    """
    List all assets. Requires ASSET_VIEW permission.
    
    Query params:
    - search: Search by name or description (supports debounced frontend search)
    - asset_type: Filter by REVENUE or SHARED
    """
    require_permission(request, Permissions.ASSET_VIEW)
    org_id = get_org_id(request)
    assets = services.list_assets(org_id, search=search, asset_type=asset_type)
    return [AssetOut(**a.__dict__) for a in assets]


@router.get("/{asset_id}", response=AssetOut, auth=None)
def get_asset(request: HttpRequest, asset_id: UUID):
    """Get asset details. Requires ASSET_VIEW permission."""
    require_permission(request, Permissions.ASSET_VIEW)
    asset = services.get_asset_dto(asset_id)
    if not asset:
        raise HttpError(404, "Asset not found")
    return AssetOut(**asset.__dict__)


@router.post("/", response=AssetOut, auth=None)
def create_asset(request: HttpRequest, payload: AssetIn):
    """Create a new asset. Requires ASSET_MANAGE permission."""
    require_permission(request, Permissions.ASSET_MANAGE)
    org_id = get_org_id(request)
    asset = services.create_asset(org_id, payload)
    return AssetOut(**asset.__dict__)


@router.put("/{asset_id}", response=AssetOut, auth=None)
def update_asset(request: HttpRequest, asset_id: UUID, payload: AssetIn):
    """Update asset. Requires ASSET_MANAGE permission."""
    require_permission(request, Permissions.ASSET_MANAGE)
    asset = services.update_asset(asset_id, payload)
    if not asset:
        raise HttpError(404, "Asset not found")
    return AssetOut(**asset.__dict__)


@router.delete("/{asset_id}", response={204: None}, auth=None)
def delete_asset(request: HttpRequest, asset_id: UUID):
    """Soft-delete asset. Requires ASSET_MANAGE permission."""
    require_permission(request, Permissions.ASSET_MANAGE)
    success = services.soft_delete_asset(asset_id)
    if not success:
        raise HttpError(404, "Asset not found")
    return 204, None


@router.post("/bulk-delete", response=dict, auth=None)
def bulk_delete_assets(request: HttpRequest, payload: BulkDeleteIn):
    """Bulk soft-delete assets. Requires ASSET_MANAGE permission."""
    require_permission(request, Permissions.ASSET_MANAGE)
    count = services.bulk_delete_assets(payload.asset_ids)
    return {"deleted": count}


# =============================================================================
# Configuration Endpoints
# =============================================================================

@router.get("/config", response=ReservationConfigOut, auth=None)
def get_config(request: HttpRequest):
    """Get reservation configuration. Requires ASSET_VIEW permission."""
    require_permission(request, Permissions.ASSET_VIEW)
    org_id = get_org_id(request)
    config = services.get_reservation_config(org_id)
    if not config:
        # Return defaults
        return ReservationConfigOut(
            id=UUID('00000000-0000-0000-0000-000000000000'),
            org_id=org_id,
            expiration_hours=services.DEFAULT_EXPIRATION_HOURS,
            allow_same_day_booking=True,
            min_advance_hours=0,
            operating_hours_start="09:00",
            operating_hours_end="22:00",
            is_active=True,
        )
    return ReservationConfigOut(**config.__dict__)


@router.post("/config", response=ReservationConfigOut, auth=None)
def update_config(request: HttpRequest, payload: ReservationConfigIn):
    """Update reservation configuration. Requires ASSET_MANAGE permission."""
    require_permission(request, Permissions.ASSET_MANAGE)
    org_id = get_org_id(request)
    config = services.create_or_update_reservation_config(
        org_id=org_id,
        expiration_hours=payload.expiration_hours,
        allow_same_day_booking=payload.allow_same_day_booking,
        min_advance_hours=payload.min_advance_hours,
        operating_hours_start=payload.operating_hours_start,
        operating_hours_end=payload.operating_hours_end,
    )
    return ReservationConfigOut(**config.__dict__)


# =============================================================================
# Analytics Endpoints (User Story #1, #2, #3)
# =============================================================================

@router.get("/analytics", response=List[AssetWithAnalyticsOut], auth=None)
def get_assets_analytics(request: HttpRequest):
    """List assets with current month income/expense. Requires ASSET_VIEW_ANALYTICS."""
    require_permission(request, Permissions.ASSET_VIEW_ANALYTICS)
    org_id = get_org_id(request)
    analytics = services.get_assets_with_analytics(org_id)
    return [
        AssetWithAnalyticsOut(
            id=a.asset_id,
            name=a.asset_name,
            asset_type=a.asset_type,
            image_url=a.image_url,
            capacity=a.capacity,
            rental_rate=a.rental_rate,
            income_this_month=a.income_this_month,
            expenses_this_month=a.expenses_this_month,
            net_income_this_month=a.net_income_this_month,
            reservation_count_this_month=a.reservation_count_this_month,
        )
        for a in analytics
    ]


@router.get("/{asset_id}/transactions", response=List[AssetTransactionOut], auth=None)
def get_asset_transactions(
    request: HttpRequest,
    asset_id: UUID,
    transaction_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Get income/expense history for an asset. Requires ASSET_VIEW_ANALYTICS."""
    require_permission(request, Permissions.ASSET_VIEW_ANALYTICS)
    transactions = services.get_asset_transactions(
        asset_id, transaction_type, start_date, end_date
    )
    return [AssetTransactionOut(**t.__dict__) for t in transactions]


# =============================================================================
# Availability Endpoints (User Story #4)
# =============================================================================

@router.get("/{asset_id}/availability", response=List[AvailabilitySlotOut], auth=None)
def get_availability(
    request: HttpRequest,
    asset_id: UUID,
    start_date: date,
    end_date: date,
):
    """Get availability schedule for an asset. Requires RESERVATION_VIEW."""
    require_permission(request, Permissions.RESERVATION_VIEW)
    slots = services.get_asset_availability(asset_id, start_date, end_date)
    return [AvailabilitySlotOut(**s.__dict__) for s in slots]


# =============================================================================
# Reservation Endpoints (User Story #5, #8, #9)
# =============================================================================

@router.post("/reservations", response=ReservationOut, auth=None)
def create_reservation(request: HttpRequest, payload: ReservationIn):
    """
    Create reservation.
    Homeowners get PENDING_PAYMENT status with expiration.
    Requires RESERVATION_CREATE.
    """
    require_permission(request, Permissions.RESERVATION_CREATE)
    org_id = get_org_id(request)
    
    try:
        reservation = services.create_reservation(
            org_id=org_id,
            data=payload,
            created_by_id=request.user.id,
            is_homeowner=is_homeowner(request),
        )
        return ReservationOut(**reservation.__dict__)
    except ValueError as e:
        raise HttpError(400, str(e))


@router.get("/reservations", response=List[ReservationOut], auth=None)
def list_reservations(
    request: HttpRequest,
    asset_id: Optional[UUID] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    List reservations.
    Homeowners see only their own unless they have VIEW_ALL.
    Requires RESERVATION_VIEW.
    """
    require_permission(request, Permissions.RESERVATION_VIEW)
    org_id = get_org_id(request)
    perms = get_user_permissions(request.user)
    
    # Homeowners can only see their own reservations
    user_filter = None
    if Permissions.RESERVATION_VIEW_ALL not in perms:
        user_filter = request.user.id
    
    reservations = services.list_reservations(
        org_id=org_id,
        asset_id=asset_id,
        reserved_by_id=user_filter,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
    return [ReservationOut(**r.__dict__) for r in reservations]


@router.get("/reservations/{reservation_id}", response=ReservationOut, auth=None)
def get_reservation(request: HttpRequest, reservation_id: UUID):
    """Get reservation details (includes breakdown info). Requires RESERVATION_VIEW."""
    require_permission(request, Permissions.RESERVATION_VIEW)
    
    reservation = services.get_reservation(reservation_id)
    if not reservation:
        raise HttpError(404, "Reservation not found")
    
    # Check access for homeowners
    perms = get_user_permissions(request.user)
    if Permissions.RESERVATION_VIEW_ALL not in perms:
        if reservation.reserved_by_id != request.user.id:
            raise HttpError(403, "Access denied")
    
    return ReservationOut(**reservation.__dict__)


@router.post("/reservations/{reservation_id}/payment", response=ReservationOut, auth=None)
def record_payment(request: HttpRequest, reservation_id: UUID, payload: ReservationPaymentIn):
    """Record payment for reservation. Requires RESERVATION_APPROVE."""
    require_permission(request, Permissions.RESERVATION_APPROVE)
    
    try:
        reservation = services.record_reservation_payment(
            reservation_id=reservation_id,
            amount=payload.amount,
            recorded_by_id=request.user.id,
            reference_number=payload.reference_number,
        )
        return ReservationOut(**reservation.__dict__)
    except ValueError as e:
        raise HttpError(400, str(e))
    except Exception as e:
        raise HttpError(404, "Reservation not found")


@router.post("/reservations/{reservation_id}/receipt", response=ReservationOut, auth=None)
def submit_receipt(request: HttpRequest, reservation_id: UUID, file: UploadedFile = File(...)):
    """
    Submit reservation receipt (proof of payment).
    Requires RESERVATION_CREATE (user own) or MANAGE (staff).
    """
    # Check permissions
    # User can upload for their own reservation, or staff can upload?
    # Requirement: "user to be able to upload a receipt"
    require_permission(request, Permissions.RESERVATION_CREATE)
    
    reservation = services.get_reservation(reservation_id)
    if not reservation:
        raise HttpError(404, "Reservation not found")
        
    # Check ownership if not staff
    perms = get_user_permissions(request.user)
    if Permissions.RESERVATION_VIEW_ALL not in perms:
        if reservation.reserved_by_id != request.user.id:
            raise HttpError(403, "Can only upload receipt for your own reservation")
            
    try:
        updated = services.submit_reservation_receipt(
            reservation_id=reservation_id,
            file=file,
            uploaded_by_id=request.user.id,
        )
        return ReservationOut(**updated.__dict__)
    except ValueError as e:
        raise HttpError(400, str(e))


@router.post("/reservations/{reservation_id}/confirm-receipt", response=ReservationOut, auth=None)
def confirm_receipt(request: HttpRequest, reservation_id: UUID):
    """
    Confirm reservation receipt.
    Requires RESERVATION_APPROVE.
    """
    require_permission(request, Permissions.RESERVATION_APPROVE)
    
    try:
        updated = services.confirm_reservation_receipt(
            reservation_id=reservation_id,
            confirmed_by_id=request.user.id,
        )
        return ReservationOut(**updated.__dict__)
    except ValueError as e:
        raise HttpError(400, str(e))


@router.post("/reservations/{reservation_id}/cancel", response=ReservationOut, auth=None)
def cancel_reservation(request: HttpRequest, reservation_id: UUID, payload: CancellationIn):
    """Cancel a reservation. Requires RESERVATION_CANCEL."""
    require_permission(request, Permissions.RESERVATION_CANCEL)
    
    reservation = services.get_reservation(reservation_id)
    if not reservation:
        raise HttpError(404, "Reservation not found")
    
    # Homeowners can only cancel their own
    perms = get_user_permissions(request.user)
    if Permissions.RESERVATION_VIEW_ALL not in perms:
        if reservation.reserved_by_id != request.user.id:
            raise HttpError(403, "Can only cancel your own reservations")
    
    try:
        cancelled = services.cancel_reservation(
            reservation_id=reservation_id,
            cancelled_by_id=request.user.id,
            reason=payload.reason,
        )
        return ReservationOut(**cancelled.__dict__)
    except ValueError as e:
        raise HttpError(400, str(e))


# =============================================================================
# Discount & Payment Preview Endpoints (User Story #6, #7)
# =============================================================================

@router.get("/discounts/applicable", response=List[DiscountPreviewOut], auth=None)
def get_applicable_discounts(request: HttpRequest):
    """Get currently applicable discounts. Requires RESERVATION_CREATE."""
    require_permission(request, Permissions.RESERVATION_CREATE)
    org_id = get_org_id(request)
    discounts = services.get_applicable_discounts(org_id)
    return [DiscountPreviewOut(**d.__dict__) for d in discounts]


@router.post("/reservations/preview", response=ReservationBreakdownOut, auth=None)
def preview_reservation(request: HttpRequest, payload: ReservationPreviewIn):
    """
    Preview payment breakdown before creating reservation.
    Available to all who can create reservations.
    Requires RESERVATION_CREATE.
    """
    require_permission(request, Permissions.RESERVATION_CREATE)
    
    try:
        breakdown = services.preview_reservation_breakdown(
            asset_id=payload.asset_id,
            start_datetime=payload.start_datetime,
            end_datetime=payload.end_datetime,
            apply_discount_ids=payload.apply_discount_ids,
        )
        return ReservationBreakdownOut(
            hourly_rate=breakdown.hourly_rate,
            hours=breakdown.hours,
            subtotal=breakdown.subtotal,
            applicable_discounts=[
                DiscountPreviewOut(**d.__dict__) 
                for d in breakdown.applicable_discounts
            ],
            selected_discount_amount=breakdown.selected_discount_amount,
            deposit_required=breakdown.deposit_required,
            total_amount=breakdown.total_amount,
        )
    except Exception as e:
        raise HttpError(400, str(e))
