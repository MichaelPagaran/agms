"""DTOs for Identity app."""
from dataclasses import dataclass
from uuid import UUID
from typing import Optional, List


@dataclass(frozen=True)
class UserDTO:
    id: UUID
    username: str
    email: str
    role: str
    org_id: Optional[UUID]
    is_active: bool
    permissions: List[str]


from ninja import Schema
from .models import UserRole

class UserCreate(Schema):
    username: str
    email: str
    password: str
    first_name: str
    last_name: str
    role: str = UserRole.HOMEOWNER
    phone: Optional[str] = None

