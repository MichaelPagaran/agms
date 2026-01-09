"""DTOs for Assets app."""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AssetDTO:
    id: UUID
    org_id: UUID
    name: str
    asset_type: str
    is_active: bool
