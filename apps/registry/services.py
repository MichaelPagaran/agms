from typing import List, Optional
from uuid import UUID
from dataclasses import dataclass
from django.db.models import Q
from .models import Unit
from .dtos import UnitIn


@dataclass(frozen=True)
class UnitDTO:
    """Data Transfer Object for Unit - used for cross-app communication."""
    id: UUID
    org_id: UUID
    section_identifier: str
    unit_identifier: str
    location_name: str
    category: str
    owner_id: Optional[UUID]
    owner_name: Optional[str]
    membership_status: str
    occupancy_status: str
    is_active: bool
    
    @property
    def full_label(self) -> str:
        return f"{self.location_name} {self.section_identifier} {self.unit_identifier}"


def get_unit_dto(unit_id: UUID) -> Optional[UnitDTO]:
    """
    Get a Unit as a DTO for cross-app communication.
    Used by ledger and other apps to validate unit references.
    """
    try:
        unit = Unit.objects.get(id=unit_id)
        return UnitDTO(
            id=unit.id,
            org_id=unit.org_id,
            section_identifier=unit.section_identifier,
            unit_identifier=unit.unit_identifier,
            location_name=unit.location_name,
            category=unit.category,
            owner_id=unit.owner_id,
            owner_name=unit.owner_name,
            membership_status=unit.membership_status,
            occupancy_status=unit.occupancy_status,
            is_active=unit.is_active,
        )
    except Unit.DoesNotExist:
        return None


def list_units(
    org_id: UUID, 
    user_id: UUID = None, 
    view_all: bool = False,
    search: str = None,
    section: str = None,
    occupancy: str = None,
    membership: str = None,
) -> List[Unit]:
    """
    List units with optional search and filtering.
    If view_all is True, return all active units for org.
    If view_all is False, return only units owned by user_id.
    """
    queryset = Unit.objects.filter(org_id=org_id, is_active=True)
    
    if not view_all:
        if user_id:
            queryset = queryset.filter(owner_id=user_id)
        else:
            return []  # Should not happen if logic is correct upstream
    
    # Apply search filter (searches multiple fields)
    if search:
        queryset = queryset.filter(
            Q(owner_name__icontains=search) |
            Q(unit_identifier__icontains=search) |
            Q(section_identifier__icontains=search) |
            Q(location_name__icontains=search) |
            Q(resident_name__icontains=search)
        )
    
    # Apply specific filters
    if section:
        queryset = queryset.filter(section_identifier=section)
    if occupancy:
        queryset = queryset.filter(occupancy_status=occupancy)
    if membership:
        queryset = queryset.filter(membership_status=membership)
            
    return list(queryset)


def get_unit_for_user(unit_id: UUID, org_id: UUID, user_id: UUID, view_all: bool = False) -> Optional[Unit]:
    """
    Get a single unit with permission checks.
    """
    try:
        queryset = Unit.objects.filter(org_id=org_id, id=unit_id, is_active=True)
        if not view_all:
             queryset = queryset.filter(owner_id=user_id)
        
        return queryset.get()
    except Unit.DoesNotExist:
        return None

def create_unit(org_id: UUID, payload: UnitIn) -> Unit:
    unit = Unit.objects.create(
        org_id=org_id,
        **payload.dict()
    )
    return unit

def update_unit(unit_id: UUID, payload: UnitIn) -> Optional[Unit]:
    try:
        unit = Unit.objects.get(id=unit_id, is_active=True)
        for attr, value in payload.dict().items():
            setattr(unit, attr, value)
        unit.save()
        return unit
    except Unit.DoesNotExist:
        return None

def soft_delete_unit(unit_id: UUID) -> bool:
    try:
        unit = Unit.objects.get(id=unit_id, is_active=True)
        unit.is_active = False
        unit.save()
        return True
    except Unit.DoesNotExist:
        return False


def get_filter_options(org_id: UUID) -> dict:
    """
    Get distinct values for filter dropdowns.
    Returns available sections, occupancy statuses, and membership statuses.
    """
    queryset = Unit.objects.filter(org_id=org_id, is_active=True)
    
    sections = list(
        queryset.values_list('section_identifier', flat=True)
        .distinct()
        .order_by('section_identifier')
    )
    
    occupancy = list(
        queryset.values_list('occupancy_status', flat=True)
        .distinct()
        .order_by('occupancy_status')
    )
    
    membership = list(
        queryset.values_list('membership_status', flat=True)
        .distinct()
        .order_by('membership_status')
    )
    
    return {
        "sections": sections,
        "occupancy": occupancy,
        "membership": membership,
    }
