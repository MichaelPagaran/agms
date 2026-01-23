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
    
    # Assets - New (Asset Manager Feature)
    ASSET_VIEW = "asset.view"
    ASSET_MANAGE = "asset.manage"
    ASSET_VIEW_ANALYTICS = "asset.view_analytics"
    
    # Reservations - New (Asset Manager Feature)
    RESERVATION_CREATE = "reservation.create"
    RESERVATION_VIEW = "reservation.view"
    RESERVATION_VIEW_ALL = "reservation.view_all"
    RESERVATION_APPROVE = "reservation.approve"
    RESERVATION_CANCEL = "reservation.cancel"


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
        # Assets - Full access
        Permissions.ASSET_VIEW,
        Permissions.ASSET_MANAGE,
        Permissions.ASSET_VIEW_ANALYTICS,
        # Reservations - Full access
        Permissions.RESERVATION_CREATE,
        Permissions.RESERVATION_VIEW,
        Permissions.RESERVATION_VIEW_ALL,
        Permissions.RESERVATION_APPROVE,
        Permissions.RESERVATION_CANCEL,
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
        Permissions.GOVERNANCE_MANAGE_DOCS,
        # Registry
        Permissions.REGISTRY_VIEW_ALL_UNITS,
        Permissions.REGISTRY_MANAGE_UNIT,
        # Assets - Can view and manage
        Permissions.ASSET_VIEW,
        Permissions.ASSET_MANAGE,
        Permissions.ASSET_VIEW_ANALYTICS,
        # Reservations - Can create, view all, approve, cancel
        Permissions.RESERVATION_CREATE,
        Permissions.RESERVATION_VIEW,
        Permissions.RESERVATION_VIEW_ALL,
        Permissions.RESERVATION_APPROVE,
        Permissions.RESERVATION_CANCEL,
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
        # Assets - Can view and manage
        Permissions.ASSET_VIEW,
        Permissions.ASSET_MANAGE,
        Permissions.ASSET_VIEW_ANALYTICS,
        # Reservations - Can create, view all, approve, cancel
        Permissions.RESERVATION_CREATE,
        Permissions.RESERVATION_VIEW,
        Permissions.RESERVATION_VIEW_ALL,
        Permissions.RESERVATION_APPROVE,
        Permissions.RESERVATION_CANCEL,
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
        # Assets - View only (including analytics)
        Permissions.ASSET_VIEW,
        Permissions.ASSET_VIEW_ANALYTICS,
        # Reservations - View only
        Permissions.RESERVATION_VIEW,
        Permissions.RESERVATION_VIEW_ALL,
    ],
    UserRole.HOMEOWNER: [
        # Governance
        Permissions.GOVERNANCE_VIEW_DOCS,
        # Limited ledger access - can view own transactions only
        # This is enforced at the service level, not here
        # Assets - View only
        Permissions.ASSET_VIEW,
        # Reservations - Can create and view own, cancel own
        Permissions.RESERVATION_CREATE,
        Permissions.RESERVATION_VIEW,  # Own only, enforced at service level
        Permissions.RESERVATION_CANCEL,  # Own only, enforced at service level
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

