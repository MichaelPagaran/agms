from ninja import Schema
from ninja.orm import create_schema
from uuid import UUID
from typing import Optional
from datetime import date
from .models import Unit

UnitOut = create_schema(Unit, exclude=['created_at', 'updated_at'])

class UnitIn(Schema):
    section_identifier: str
    unit_identifier: str
    location_name: str
    category: str
    owner_id: Optional[UUID] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    owner_phone: Optional[str] = None
    resident_name: Optional[str] = None
    membership_status: Optional[str] = "GOOD_STANDING"
    occupancy_status: Optional[str] = "INHABITED"
    # is_active handles soft delete, not usually set here unless restoring

class DeleteRequestIn(Schema):
    unit_ids: list[UUID]

