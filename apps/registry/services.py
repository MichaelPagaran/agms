from typing import List, Optional
from uuid import UUID
from django.db.models import Q
from .models import Unit
from .dtos import UnitIn

def list_units(org_id: UUID, user_id: UUID = None, view_all: bool = False) -> List[Unit]:
    """
    List units.
    If view_all is True, return all active units for org.
    If view_all is False, return only units owned by user_id.
    """
    queryset = Unit.objects.filter(org_id=org_id, is_active=True)
    
    if not view_all:
        if user_id:
            queryset = queryset.filter(owner_id=user_id)
        else:
            return [] # Should not happen if logic is correct upstream
            
    return list(queryset)

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
