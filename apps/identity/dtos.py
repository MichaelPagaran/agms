"""DTOs for Identity app."""
from dataclasses import dataclass
from uuid import UUID
from typing import Optional


@dataclass(frozen=True)
class UserDTO:
    id: UUID
    username: str
    email: str
    role: str
    org_id: Optional[UUID]
    is_active: bool
