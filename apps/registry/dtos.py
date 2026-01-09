"""DTOs for Registry app."""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class UnitDTO:
    id: UUID
    org_id: UUID
    full_label: str
    owner_name: str
    membership_status: str
    is_active: bool
