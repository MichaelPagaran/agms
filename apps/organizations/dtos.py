from ninja import Schema
from ninja.orm import create_schema
from uuid import UUID
from typing import Optional, Dict, Any
from .models import Organization

OrganizationOut = create_schema(Organization, exclude=['created_at', 'updated_at'])

class OrganizationIn(Schema):
    name: str
    org_type: str = "SUBDIVISION" # SUBDIVISION or CONDOMINIUM
    settings: Dict[str, Any] = {}
    logo: Optional[str] = None
    tin: Optional[str] = None
    dhsud_registration: Optional[str] = None
    address: Optional[str] = None
    fiscal_year_start_month: int = 1
    is_active: bool = True


from apps.identity.dtos import UserCreate, UserDTO

class OnboardingRequest(Schema):
    organization: OrganizationIn
    admin_user: UserCreate

class OnboardingResponse(Schema):
    organization: OrganizationOut
    admin_user: UserDTO
