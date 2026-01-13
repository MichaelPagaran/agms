from typing import List, Dict
from .models import UserRole, User

# Define all available permissions here for reference
class Permissions:
    # Ledger - Existing
    LEDGER_VIEW_EXPENSE = "ledger.view_expense"
    LEDGER_CREATE_EXPENSE = "ledger.create_expense"
    LEDGER_APPROVE_EXPENSE = "ledger.approve_expense"
    LEDGER_VIEW_REPORT = "ledger.view_report"
    
    # Ledger - New (Financial Ledger Feature)
    LEDGER_VIEW_TRANSACTIONS = "ledger.view_transactions"
    LEDGER_CREATE_INCOME = "ledger.create_income"
    LEDGER_EDIT_TRANSACTION = "ledger.edit_transaction"
    LEDGER_CANCEL_TRANSACTION = "ledger.cancel_transaction"
    LEDGER_MANAGE_CONFIG = "ledger.manage_config"
    LEDGER_REQUIRE_RECEIPT = "ledger.require_receipt"
    
    # Identity
    IDENTITY_VIEW_USER = "identity.view_user"
    IDENTITY_MANAGE_USER = "identity.manage_user"
    
    # Governance
    GOVERNANCE_VIEW_DOCS = "governance.view_docs"
    GOVERNANCE_MANAGE_DOCS = "governance.manage_docs"
    
    # Registry
    REGISTRY_VIEW_ALL_UNITS = "registry.view_all_units"
    REGISTRY_MANAGE_UNIT = "registry.manage_unit"
    
    # Organizations
    ORGANIZATION_MANAGE = "organization.manage"


# Static Role -> Permission Mapping
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    UserRole.ADMIN: [
        # Ledger - Full access
        Permissions.LEDGER_VIEW_EXPENSE,
        Permissions.LEDGER_CREATE_EXPENSE,
        Permissions.LEDGER_APPROVE_EXPENSE,
        Permissions.LEDGER_VIEW_REPORT,
        Permissions.LEDGER_VIEW_TRANSACTIONS,
        Permissions.LEDGER_CREATE_INCOME,
        Permissions.LEDGER_EDIT_TRANSACTION,
        Permissions.LEDGER_CANCEL_TRANSACTION,
        Permissions.LEDGER_MANAGE_CONFIG,
        Permissions.LEDGER_REQUIRE_RECEIPT,
        # Identity
        Permissions.IDENTITY_VIEW_USER,
        Permissions.IDENTITY_MANAGE_USER,
        # Governance
        Permissions.GOVERNANCE_VIEW_DOCS,
        Permissions.GOVERNANCE_MANAGE_DOCS,
        # Registry
        Permissions.REGISTRY_VIEW_ALL_UNITS,
        Permissions.REGISTRY_MANAGE_UNIT,
        # Organizations
        Permissions.ORGANIZATION_MANAGE,
    ],
    UserRole.STAFF: [
        # Ledger - Can create but not approve or cancel
        Permissions.LEDGER_VIEW_EXPENSE,
        Permissions.LEDGER_CREATE_EXPENSE,
        Permissions.LEDGER_VIEW_REPORT,
        Permissions.LEDGER_VIEW_TRANSACTIONS,
        Permissions.LEDGER_CREATE_INCOME,
        Permissions.LEDGER_EDIT_TRANSACTION,
        # Identity
        Permissions.IDENTITY_VIEW_USER,
        # Governance
        Permissions.GOVERNANCE_VIEW_DOCS,
        # Registry
        Permissions.REGISTRY_VIEW_ALL_UNITS,
        Permissions.REGISTRY_MANAGE_UNIT,
    ],
    UserRole.BOARD: [
        # Ledger - Can approve, cancel, and manage config
        Permissions.LEDGER_VIEW_EXPENSE,
        Permissions.LEDGER_APPROVE_EXPENSE,
        Permissions.LEDGER_VIEW_REPORT,
        Permissions.LEDGER_VIEW_TRANSACTIONS,
        Permissions.LEDGER_CANCEL_TRANSACTION,
        Permissions.LEDGER_MANAGE_CONFIG,
        Permissions.LEDGER_REQUIRE_RECEIPT,
        # Identity
        Permissions.IDENTITY_VIEW_USER,
        # Governance
        Permissions.GOVERNANCE_VIEW_DOCS,
        Permissions.GOVERNANCE_MANAGE_DOCS,
        # Registry
        Permissions.REGISTRY_VIEW_ALL_UNITS,
        Permissions.REGISTRY_MANAGE_UNIT,
    ],
    UserRole.AUDITOR: [
        # Ledger - View only
        Permissions.LEDGER_VIEW_EXPENSE,
        Permissions.LEDGER_VIEW_REPORT,
        Permissions.LEDGER_VIEW_TRANSACTIONS,
        # Governance
        Permissions.GOVERNANCE_VIEW_DOCS,
        # Registry
        Permissions.REGISTRY_VIEW_ALL_UNITS,
    ],
    UserRole.HOMEOWNER: [
        # Governance
        Permissions.GOVERNANCE_VIEW_DOCS,
        # Limited ledger access - can view own transactions only
        # This is enforced at the service level, not here
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
