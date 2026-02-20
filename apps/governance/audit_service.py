"""
Centralized audit logging service.

Use log_action() to record any critical mutation. It is designed to be
fire-and-forget — it will never raise, so a logging failure will never
break the calling request.

Usage:
    from apps.governance.audit_service import log_action, AuditAction

    log_action(
        org_id=org_id,
        action=AuditAction.CREATE_INCOME,
        target_type="Transaction",
        target_id=transaction.id,
        target_label=f"Income ₱{amount} – {category}",
        performed_by=request.user,
        context={"amount": str(amount), "category": category},
    )
"""
from uuid import UUID
from typing import Optional

from .models import AuditLog


class AuditAction:
    """
    Canonical string constants for audit log actions.
    Prevents scattered string literals and typos across apps.
    """
    # ── Ledger – Transactions ─────────────────────────────────────────
    CREATE_INCOME = "CREATE_INCOME"
    CREATE_EXPENSE = "CREATE_EXPENSE"
    VERIFY_TRANSACTION = "VERIFY_TRANSACTION"
    CANCEL_TRANSACTION = "CANCEL_TRANSACTION"

    # ── Ledger – Configuration ────────────────────────────────────────
    CREATE_CATEGORY = "CREATE_CATEGORY"
    CREATE_DISCOUNT = "CREATE_DISCOUNT"
    CREATE_PENALTY = "CREATE_PENALTY"
    UPDATE_BILLING_CONFIG = "UPDATE_BILLING_CONFIG"

    # ── Assets ────────────────────────────────────────────────────────
    CREATE_ASSET = "CREATE_ASSET"
    UPDATE_ASSET = "UPDATE_ASSET"
    DELETE_ASSET = "DELETE_ASSET"
    UPDATE_ASSET_CONFIG = "UPDATE_ASSET_CONFIG"

    # ── Reservations ──────────────────────────────────────────────────
    CREATE_RESERVATION = "CREATE_RESERVATION"
    RECORD_PAYMENT = "RECORD_PAYMENT"
    CONFIRM_RECEIPT = "CONFIRM_RECEIPT"
    CANCEL_RESERVATION = "CANCEL_RESERVATION"

    # ── Governance ────────────────────────────────────────────────────
    APPROVE_REQUEST = "APPROVE_REQUEST"
    REJECT_REQUEST = "REJECT_REQUEST"

    # ── Registry ──────────────────────────────────────────────────────
    CREATE_UNIT = "CREATE_UNIT"
    UPDATE_UNIT = "UPDATE_UNIT"
    DELETE_UNIT = "DELETE_UNIT"


def log_action(
    *,
    org_id: UUID,
    action: str,
    target_type: str,
    target_id: UUID,
    performed_by,
    target_label: str = "",
    context: Optional[dict] = None,
) -> Optional[AuditLog]:
    """
    Create an AuditLog entry for a critical action.

    Never raises — any DB or serialization error is silently swallowed so
    audit logging never degrades the user-facing request.

    Args:
        org_id:        Organisation UUID for multi-tenant isolation.
        action:        Action constant from AuditAction (e.g. "CREATE_INCOME").
        target_type:   Human-readable type of the object acted on (e.g. "Transaction").
        target_id:     Primary key of the object acted on.
        performed_by:  Django User instance or None.
        target_label:  Optional human-readable description of the object.
        context:       Optional dict of additional metadata to store as JSON.

    Returns:
        The created AuditLog instance, or None if creation failed.
    """
    try:
        return AuditLog.objects.create(
            org_id=org_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            target_label=target_label,
            performed_by=performed_by,
            context=context or {},
        )
    except Exception:
        # Safety net: never let audit logging break a request
        return None
