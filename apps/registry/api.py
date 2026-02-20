"""
Registry API endpoints with JWT authentication.

Provides CRUD operations for property units (lots/blocks or units/floors).
"""
from typing import List, Optional
from uuid import UUID
from ninja import Router
from ninja.errors import HttpError
from django.http import HttpRequest

from apps.identity.api import get_current_user, require_auth
from apps.identity.permissions import Permissions, get_user_permissions
from django.http import HttpRequest
from ninja import Router

from apps.identity.decorators import has_permission
from apps.identity.permissions import Permissions
from apps.identity.api import require_auth
from apps.governance.models import AuditLog
from apps.governance.audit_service import log_action, AuditAction
from .models import Unit
from .dtos import UnitOut, UnitIn, DeleteRequestIn
from .services import list_units, create_unit, update_unit, soft_delete_unit, get_filter_options, get_unit_for_user

router = Router(tags=["Registry"])

@router.post("/bulk-delete", auth=None)
@has_permission(Permissions.REGISTRY_MANAGE_UNIT)
def bulk_delete_units_api(request: HttpRequest, payload: DeleteRequestIn):
    """
    Bulk soft delete units and create audit logs.
    """
    user = request.user
    
    if not user.org_id_id:
        raise HttpError(400, "User has no organization context")
        
    if not user.org_id_id:
        raise HttpError(400, "User has no organization context")

    deleted_count = 0
    
    # Process deletions
    units = Unit.objects.filter(id__in=payload.unit_ids, org_id=user.org_id_id, is_active=True)
    
    for unit in units:
        # Soft delete
        unit.is_active = False
        unit.save()
        deleted_count += 1
        
        # Log audit via centralized service
        log_action(
            org_id=user.org_id_id,
            action=AuditAction.DELETE_UNIT,
            target_type="Unit",
            target_id=unit.id,
            target_label=unit.full_label,
            performed_by=user,
            context={"unit_id": str(unit.id)},
        )
        
    return {"deleted": deleted_count}


@router.get("/filter-options", auth=None)
def get_filter_options_api(request: HttpRequest):
    """
    Get distinct values for filter dropdowns.
    Returns available sections, occupancy statuses, and membership statuses.
    """
    user = require_auth(request)
    
    if not user.org_id_id:
        return {"sections": [], "occupancy": [], "membership": []}
    
    return get_filter_options(user.org_id_id)


@router.get("", response=List[UnitOut], auth=None)
def get_units(
    request: HttpRequest,
    search: Optional[str] = None,
    section: Optional[str] = None,
    occupancy: Optional[str] = None,
    membership: Optional[str] = None,
):
    """
    List all units in the organization with optional search and filtering.
    
    Query Parameters:
    - search: Search in owner_name, unit_identifier, section_identifier, location_name
    - section: Filter by section_identifier (block)
    - occupancy: Filter by occupancy_status (INHABITED, VACANT, UNDER_CONSTRUCTION)
    - membership: Filter by membership_status (GOOD_STANDING, DELINQUENT, NON_MEMBER)
    
    - Admins/Staff see all units
    - Homeowners see only their own unit
    """
    user = require_auth(request)
    perms = get_user_permissions(user)
    
    can_view_all = Permissions.REGISTRY_VIEW_ALL_UNITS in perms
    
    if not user.org_id_id:
        return []
    
    return list_units(
        user.org_id_id, 
        user.id, 
        view_all=can_view_all,
        search=search,
        section=section,
        occupancy=occupancy,
        membership=membership,
    )


@router.get("/{unit_id}", response=UnitOut, auth=None)
def get_unit_api(request: HttpRequest, unit_id: UUID):
    """
    Get details of a single unit.
    """
    user = require_auth(request)
    perms = get_user_permissions(user)
    
    if not user.org_id_id:
        raise HttpError(404, "Unit not found")
        
    can_view_all = Permissions.REGISTRY_VIEW_ALL_UNITS in perms
    
    unit = get_unit_for_user(unit_id, user.org_id_id, user.id, view_all=can_view_all)
    
    if not unit:
        raise HttpError(404, "Unit not found")
        
    return unit



@router.post("", response=UnitOut, auth=None)
@has_permission(Permissions.REGISTRY_MANAGE_UNIT)
def create_unit_api(request: HttpRequest, payload: UnitIn):
    """
    Create a new unit in the organization.
    
    Requires REGISTRY_MANAGE_UNIT permission.
    """
    user = request.user
    if not user.org_id_id:
        raise HttpError(400, "User has no organization context")

    unit = create_unit(user.org_id_id, payload)
    log_action(
        org_id=user.org_id_id,
        action=AuditAction.CREATE_UNIT,
        target_type="Unit",
        target_id=unit.id,
        target_label=unit.full_label if hasattr(unit, 'full_label') else str(unit.id),
        performed_by=user,
        context={"unit_id": str(unit.id)},
    )
    return unit


@router.put("/{unit_id}", response=UnitOut, auth=None)
@has_permission(Permissions.REGISTRY_MANAGE_UNIT)
def update_unit_api(request: HttpRequest, unit_id: UUID, payload: UnitIn):
    """
    Update an existing unit.
    
    Requires REGISTRY_MANAGE_UNIT permission.
    """
    unit = update_unit(unit_id, payload)
    if not unit:
        raise HttpError(404, "Unit not found")
    log_action(
        org_id=request.user.org_id_id,
        action=AuditAction.UPDATE_UNIT,
        target_type="Unit",
        target_id=unit_id,
        target_label=str(unit_id),
        performed_by=request.user,
        context={"unit_id": str(unit_id)},
    )
    return unit


@router.delete("/{unit_id}", response={204: None}, auth=None)
@has_permission(Permissions.REGISTRY_MANAGE_UNIT)
def delete_unit_api(request: HttpRequest, unit_id: UUID):
    """
    Soft delete a unit.
    
    Requires REGISTRY_MANAGE_UNIT permission.
    """
    # Authorization handled by decorator
    success = soft_delete_unit(unit_id)
    if not success:
        raise HttpError(404, "Unit not found")
    log_action(
        org_id=request.user.org_id_id,
        action=AuditAction.DELETE_UNIT,
        target_type="Unit",
        target_id=unit_id,
        target_label=str(unit_id),
        performed_by=request.user,
        context={"unit_id": str(unit_id)},
    )
    return 204

