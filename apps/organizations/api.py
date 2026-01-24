from typing import List
from uuid import UUID
from ninja import Router
from ninja.errors import HttpError
from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from apps.identity.permissions import Permissions
from apps.identity.security import has_permission
from .models import Organization
from .dtos import OrganizationOut, OrganizationIn, OnboardingRequest, OnboardingResponse
from .services import onboard_organization

router = Router(tags=["Organizations"])

@router.post("/onboard", response=OnboardingResponse, auth=None)
def create_onboard(request: HttpRequest, payload: OnboardingRequest):
    """
    **Public Endpoint**: Register a new Organization.
    
    This creates:
    1. A new Organization tenant.
    2. An 'Initial Administrator' user linked to that organization.
    
    No authentication is required.
    """
    return onboard_organization(payload)

@router.post("", response=OrganizationOut, auth=None)
def create_organization(request: HttpRequest, payload: OrganizationIn):
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")
        
    # Strictly for users with Manage Org permission
    from apps.identity.permissions import get_user_permissions
    perms = get_user_permissions(request.user)
    if Permissions.ORGANIZATION_MANAGE not in perms:
        raise HttpError(403, "Permission denied")

    org = Organization.objects.create(**payload.dict())
    return org

@router.get("", response=List[OrganizationOut], auth=None)
def list_organizations(request: HttpRequest):
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")

    from apps.identity.permissions import get_user_permissions
    perms = get_user_permissions(request.user)
    if Permissions.ORGANIZATION_MANAGE not in perms:
        raise HttpError(403, "Permission denied")

    return list(Organization.objects.all())

@router.get("/{org_id}", response=OrganizationOut, auth=None)
def get_organization(request: HttpRequest, org_id: UUID):
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")
        
    # TODO: Allow Tenant Admin to see OWN org?
    # For now, restrict to Manage Org permission
    from apps.identity.permissions import get_user_permissions
    perms = get_user_permissions(request.user)
    if Permissions.ORGANIZATION_MANAGE not in perms:
        raise HttpError(403, "Permission denied")
        
    return get_object_or_404(Organization, id=org_id)

@router.put("/{org_id}", response=OrganizationOut, auth=None)
def update_organization(request: HttpRequest, org_id: UUID, payload: OrganizationIn):
    if not request.user.is_authenticated:
        raise HttpError(401, "Unauthorized")

    from apps.identity.permissions import get_user_permissions
    perms = get_user_permissions(request.user)
    if Permissions.ORGANIZATION_MANAGE not in perms:
        raise HttpError(403, "Permission denied")
    
    org = get_object_or_404(Organization, id=org_id)
    for attr, value in payload.dict().items():
        setattr(org, attr, value)
    org.save()
    return org
