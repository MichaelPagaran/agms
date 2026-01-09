"""Services for Registry app - the public API for other apps."""
from .models import Unit
from .dtos import UnitDTO


def get_unit_dto(unit_id) -> UnitDTO | None:
    """Get a unit by ID and return as DTO."""
    try:
        unit = Unit.objects.get(id=unit_id)
        return UnitDTO(
            id=unit.id,
            org_id=unit.org_id,
            full_label=unit.full_label,
            owner_name=unit.owner_name,
            membership_status=unit.membership_status,
            is_active=unit.is_active,
        )
    except Unit.DoesNotExist:
        return None


def get_units_by_org(org_id) -> list[UnitDTO]:
    """Get all units for an organization."""
    units = Unit.objects.filter(org_id=org_id, is_active=True)
    return [
        UnitDTO(
            id=u.id,
            org_id=u.org_id,
            full_label=u.full_label,
            owner_name=u.owner_name,
            membership_status=u.membership_status,
            is_active=u.is_active,
        )
        for u in units
    ]
