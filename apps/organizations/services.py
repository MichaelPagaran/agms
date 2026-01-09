"""
Services for Organizations app.
This is the public API for other apps to interact with organizations.
"""
from .models import Organization
from .dtos import OrganizationDTO


def get_organization_dto(org_id) -> OrganizationDTO | None:
    """
    Get an organization by ID and return as DTO.
    This is the only way other apps should access organization data.
    """
    try:
        org = Organization.objects.get(id=org_id)
        return OrganizationDTO(
            id=org.id,
            name=org.name,
            org_type=org.org_type,
            settings=org.settings,
            is_active=org.is_active,
        )
    except Organization.DoesNotExist:
        return None
