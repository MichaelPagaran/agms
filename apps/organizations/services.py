"""
Services for Organizations app.
This is the public API for other apps to interact with organizations.
"""
from django.db import transaction
from .models import Organization
from .dtos import OnboardingRequest, OnboardingResponse, OrganizationOut
from apps.identity.services import create_user
from apps.identity.models import UserRole

def get_organization_dto(org_id) -> OrganizationOut | None:
    """
    Get an organization by ID and return as DTO.
    This is the only way other apps should access organization data.
    """
    try:
        org = Organization.objects.get(id=org_id)
        return OrganizationOut.from_orm(org)
    except Organization.DoesNotExist:
        return None

def onboard_organization(payload: OnboardingRequest) -> OnboardingResponse:
    with transaction.atomic():
        # 1. Create Organization
        org_data = payload.organization.dict()
        org = Organization.objects.create(**org_data)
        
        # 2. Create Admin User
        user_payload = payload.admin_user
        # Enforce ADMIN role
        user_payload.role = UserRole.ADMIN
        
        user_dto = create_user(org_id=org.id, payload=user_payload)
        
        # 3. Construct response
        # We need OrganizationOut from the org model instance
        org_out = OrganizationOut.from_orm(org)
        
        return OnboardingResponse(
            organization=org_out,
            admin_user=user_dto
        )
