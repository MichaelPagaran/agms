from typing import List, Dict
from .models import UserRole, User

# Define all available permissions here for reference
class Permissions:
    # Ledger
    LEDGER_VIEW_EXPENSE = "ledger.view_expense"
    LEDGER_CREATE_EXPENSE = "ledger.create_expense"
    LEDGER_APPROVE_EXPENSE = "ledger.approve_expense"
    LEDGER_VIEW_REPORT = "ledger.view_report"
    
    # Identity
    IDENTITY_VIEW_USER = "identity.view_user"
    IDENTITY_MANAGE_USER = "identity.manage_user"
    
    # Governance
    GOVERNANCE_VIEW_DOCS = "governance.view_docs"
    GOVERNANCE_MANAGE_DOCS = "governance.manage_docs"
    
    # Registry
    REGISTRY_VIEW_ALL_UNITS = "registry.view_all_units"
    REGISTRY_MANAGE_UNIT = "registry.manage_unit"


# Static Role -> Permission Mapping
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    UserRole.ADMIN: [
        Permissions.LEDGER_VIEW_EXPENSE,
        Permissions.LEDGER_CREATE_EXPENSE,
        Permissions.LEDGER_APPROVE_EXPENSE,
        Permissions.LEDGER_VIEW_REPORT,
        Permissions.IDENTITY_VIEW_USER,
        Permissions.IDENTITY_MANAGE_USER,
        Permissions.GOVERNANCE_VIEW_DOCS,
        Permissions.GOVERNANCE_MANAGE_DOCS,
        Permissions.REGISTRY_VIEW_ALL_UNITS,
        Permissions.REGISTRY_MANAGE_UNIT,
    ],
    UserRole.STAFF: [
        Permissions.LEDGER_VIEW_EXPENSE,
        Permissions.LEDGER_CREATE_EXPENSE,
        Permissions.LEDGER_VIEW_REPORT,
        Permissions.IDENTITY_VIEW_USER,
        Permissions.GOVERNANCE_VIEW_DOCS,
        Permissions.REGISTRY_VIEW_ALL_UNITS,
        Permissions.REGISTRY_MANAGE_UNIT,
    ],
    UserRole.BOARD: [
        Permissions.LEDGER_VIEW_EXPENSE,
        Permissions.LEDGER_APPROVE_EXPENSE,
        Permissions.LEDGER_VIEW_REPORT,
        Permissions.IDENTITY_VIEW_USER,
        Permissions.GOVERNANCE_VIEW_DOCS,
        Permissions.GOVERNANCE_MANAGE_DOCS,
        Permissions.REGISTRY_VIEW_ALL_UNITS,
        Permissions.REGISTRY_MANAGE_UNIT,
    ],
    UserRole.AUDITOR: [
        Permissions.LEDGER_VIEW_EXPENSE,
        Permissions.LEDGER_VIEW_REPORT,
        Permissions.GOVERNANCE_VIEW_DOCS,
        Permissions.REGISTRY_VIEW_ALL_UNITS,
    ],
    UserRole.HOMEOWNER: [
        Permissions.GOVERNANCE_VIEW_DOCS,
        # Homeowners do NOT get generic view_all, they rely on 'view own' logic
    ],
}

def get_user_permissions(user: User) -> List[str]:
    """
    Returns a list of permission strings for the given user based on their role.
    """
    if not user or not user.is_active:
        return []
        
    # Superusers get all permissions implicitly? 
    # For now, let's treat them as ADMIN plus extra if needed, 
    # but strictly following the map is safer for now.
    
    return ROLE_PERMISSIONS.get(user.role, [])
