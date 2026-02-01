from typing import List
from uuid import UUID
from ninja import Router
from ninja.errors import HttpError
from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from apps.identity.decorators import has_permission
from apps.identity.permissions import Permissions
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
@has_permission(Permissions.ORGANIZATION_MANAGE)
def create_organization(request: HttpRequest, payload: OrganizationIn):
    # Only super-admins should be able to create arbitrary organizations manually
    # But for now we just stick to permission check
    org = Organization.objects.create(**payload.dict())
    return org

@router.get("", response=List[OrganizationOut], auth=None)
@has_permission(Permissions.ORGANIZATION_MANAGE)
def list_organizations(request: HttpRequest):
    # If superuser or platform admin, show all
    # For Tenant Admin, only show their own organization
    if request.user.is_superuser:
        return list(Organization.objects.all())
    
    if request.user.org_id_id:
        return list(Organization.objects.filter(id=request.user.org_id_id))
        
    return []

@router.get("/{org_id}", response=OrganizationOut, auth=None)
@has_permission(Permissions.ORGANIZATION_MANAGE)
def get_organization(request: HttpRequest, org_id: UUID):
    # Enforce strict tenant isolation:
    # Users can only view their own organization, unless they are superusers
    if not request.user.is_superuser:
        if request.user.org_id_id != org_id:
             raise HttpError(403, "Permission denied: Cannot view other organizations")
        
    return get_object_or_404(Organization, id=org_id)

@router.put("/{org_id}", response=OrganizationOut, auth=None)
@has_permission(Permissions.ORGANIZATION_MANAGE)
def update_organization(request: HttpRequest, org_id: UUID, payload: OrganizationIn):
    # Enforce strict tenant isolation
    if not request.user.is_superuser:
        if request.user.org_id_id != org_id:
             raise HttpError(403, "Permission denied: Cannot update other organizations")

    org = get_object_or_404(Organization, id=org_id)
    for attr, value in payload.dict().items():
        setattr(org, attr, value)
    org.save()
    return org
