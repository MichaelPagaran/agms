from typing import List
from uuid import UUID
from ninja import Router
from ninja.errors import HttpError
from django.http import HttpRequest

from apps.identity.permissions import Permissions
from apps.identity.security import has_permission
from .dtos import UnitOut, UnitIn
from .services import list_units, create_unit, update_unit, soft_delete_unit

router = Router()

@router.get("", response=List[UnitOut], auth=None)
# NOTE: We can't trivially use 'has_permission' decorator here because logic forks:
# - Admin/Staff/etc get all.
# - Homeowner gets own.
def get_units(request: HttpRequest):
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")
    
    # Check if user has "view all" permission
    from apps.identity.permissions import get_user_permissions
    perms = get_user_permissions(request.user)
    
    can_view_all = Permissions.REGISTRY_VIEW_ALL_UNITS in perms
    
    # For now, hardcode ORG_ID or extract from user if we had tenancy. 
    # For single tenant mode/MVP, let's assume one org or derived from user.
    # But wait, User model has 'org_id'.
    org_id = request.user.org_id
    if not org_id:
        # Fallback or error? For MVP let's require org_id or handle gracefully
        # If null, maybe 400? Or just empty list?
        # Let's mock a UUID if testing without orgs, but better to check user.
        # Ensure your seed users have IDs. 
        # For now, if no org_id, return empty.
        pass

    # Actually, for test simplicity, if user.org_id is None, creating unit will fail on UUID field.
    # The models say org_id is UUID.
    # Let's assume user has it.
    
    # Wait, the seeded users might have null org_id?
    # models.py: org_id = models.UUIDField(null=True, blank=True, db_index=True)
    # If null, let's use a dummy or just empty.
    if not org_id:
         # For testing purposes if seed didn't set org, we might have issues.
         # But the function needs it.
         import uuid
         # Fallback to a zero UUID or something if truly needed? 
         # Or filter(org_id__isnull=True)?
         # Service expects UUID value.
         pass

    # FIX: Service `list_units` requires org_id. 
    # Let's make it optional in service or handle here.
    # If no org_id on user, they see nothing?
    if not request.user.org_id:
         # Should we return empty list?
         return []

    return list_units(request.user.org_id, request.user.id, view_all=can_view_all)


@router.post("", response=UnitOut, auth=None)
def create_unit_api(request: HttpRequest, payload: UnitIn):
    # Enforce permission
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")
    
    # Manual check since we aren't using the decorator for the whole router yet (mixed access)
    # But this route IS strict.
    from apps.identity.permissions import get_user_permissions
    perms = get_user_permissions(request.user)
    if Permissions.REGISTRY_MANAGE_UNIT not in perms:
        raise HttpError(403, "Permission denied")

    # Org ID
    if not request.user.org_id:
         # Cannot create unit without org context
         raise HttpError(400, "User has no organization context")

    return create_unit(request.user.org_id, payload)


@router.put("/{unit_id}", response=UnitOut, auth=None)
def update_unit_api(request: HttpRequest, unit_id: UUID, payload: UnitIn):
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")
        
    from apps.identity.permissions import get_user_permissions
    perms = get_user_permissions(request.user)
    if Permissions.REGISTRY_MANAGE_UNIT not in perms:
        raise HttpError(403, "Permission denied")

    unit = update_unit(unit_id, payload)
    if not unit:
        raise HttpError(404, "Unit not found")
    return unit


@router.delete("/{unit_id}", response={204: None}, auth=None)
def delete_unit_api(request: HttpRequest, unit_id: UUID):
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")

    from apps.identity.permissions import get_user_permissions
    perms = get_user_permissions(request.user)
    if Permissions.REGISTRY_MANAGE_UNIT not in perms:
        raise HttpError(403, "Permission denied")
        
    success = soft_delete_unit(unit_id)
    if not success:
        raise HttpError(404, "Unit not found")
    return 204
