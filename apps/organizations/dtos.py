"""
DTOs for Organizations app.
These are the data structures exposed to other apps.
"""
from dataclasses import dataclass
from uuid import UUID
from typing import Dict, Any


@dataclass(frozen=True)
class OrganizationDTO:
    id: UUID
    name: str
    org_type: str
    settings: Dict[str, Any]
    is_active: bool
