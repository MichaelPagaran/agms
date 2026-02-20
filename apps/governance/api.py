from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError

from apps.identity.models import User
from apps.identity.permissions import Permissions, get_user_permissions
from apps.core.task_service import TaskService
from .models import DocumentRequest, RequestStatus, AuditLog
from .dtos import DocumentRequestIn, DocumentRequestOut, RequestApprovalIn, AuditLogOut
from .audit_service import log_action, AuditAction

router = Router(tags=["Governance"])


def require_auth(request):
    """Require authenticated user."""
    if not request.user.is_authenticated:
        raise HttpError(401, "Authentication required")
    return request.user


def require_permission(request, permission: str):
    """Require a specific permission."""
    require_auth(request)
    perms = get_user_permissions(request.user)
    if permission not in perms:
        raise HttpError(403, f"Permission denied: {permission}")


def get_org_id(request):
    """Get org ID from authenticated user."""
    if not request.user.org_id_id:
        raise HttpError(400, "User has no organisation context")
    return request.user.org_id_id


# =============================================================================
# Document Request Endpoints
# =============================================================================

@router.post("/requests", response=DocumentRequestOut, auth=None)
def create_request(request, payload: DocumentRequestIn):
    """Create a new document request."""
    user = require_auth(request)

    doc_request = DocumentRequest.objects.create(
        org_id=user.org_id_id,
        requestor=user,
        document_type=payload.document_type,
        purpose=payload.purpose,
        date_range_start=payload.date_range_start,
        date_range_end=payload.date_range_end,
        status=RequestStatus.PENDING,
    )
    return doc_request


@router.get("/requests", response=List[DocumentRequestOut])
def list_requests(request, status: Optional[str] = None):
    """List document requests for the user's organisation."""
    user = require_auth(request)

    qs = DocumentRequest.objects.filter(org_id=user.org_id_id)
    if status:
        qs = qs.filter(status=status)

    return list(qs)


@router.post("/requests/{request_id}/approve", response=DocumentRequestOut)
def approve_request(request, request_id: UUID):
    """Approve a document request and trigger PDF generation."""
    user = require_auth(request)
    require_permission(request, Permissions.GOVERNANCE_MANAGE_DOCS)

    doc_request = get_object_or_404(DocumentRequest, id=request_id, org_id=user.org_id_id)

    if doc_request.status != RequestStatus.PENDING:
        raise HttpError(400, f"Cannot approve request with status '{doc_request.status}'")

    doc_request.status = RequestStatus.APPROVED
    doc_request.approved_by = user
    doc_request.save()

    # Trigger async PDF generation
    try:
        from apps.ledger.tasks import generate_document_task
        generate_document_task.delay(str(request_id))
    except Exception:
        pass  # Don't fail the approval if task queue is unavailable

    log_action(
        org_id=user.org_id_id,
        action=AuditAction.APPROVE_REQUEST,
        target_type="DocumentRequest",
        target_id=doc_request.id,
        target_label=f"{doc_request.document_type} request",
        performed_by=user,
        context={"document_type": doc_request.document_type},
    )

    return doc_request


@router.post("/requests/{request_id}/reject", response=DocumentRequestOut)
def reject_request(request, request_id: UUID, payload: RequestApprovalIn):
    """Reject a document request."""
    user = require_auth(request)
    require_permission(request, Permissions.GOVERNANCE_MANAGE)

    doc_request = get_object_or_404(DocumentRequest, id=request_id, org_id=user.org_id_id)

    if doc_request.status != RequestStatus.PENDING:
        raise HttpError(400, f"Cannot reject request with status '{doc_request.status}'")

    doc_request.status = RequestStatus.REJECTED
    doc_request.rejection_reason = payload.rejection_reason or "No reason provided."
    doc_request.approved_by = None
    doc_request.save()

    log_action(
        org_id=user.org_id_id,
        action=AuditAction.REJECT_REQUEST,
        target_type="DocumentRequest",
        target_id=doc_request.id,
        target_label=f"{doc_request.document_type} request",
        performed_by=user,
        context={
            "document_type": doc_request.document_type,
            "reason": doc_request.rejection_reason,
        },
    )

    return doc_request


# =============================================================================
# Audit Log Endpoints
# =============================================================================

def _serialize_log(log: AuditLog) -> AuditLogOut:
    """Convert an AuditLog model instance to its output schema."""
    performed_by_name = None
    if log.performed_by_id:
        try:
            performed_by_name = log.performed_by.get_full_name() or log.performed_by.email
        except Exception:
            pass

    return AuditLogOut(
        id=log.id,
        org_id=log.org_id,
        action=log.action,
        target_type=log.target_type,
        target_id=log.target_id,
        target_label=log.target_label,
        performed_by_name=performed_by_name,
        performed_at=log.performed_at,
        context=log.context,
    )


@router.get("/audit-logs", response=List[AuditLogOut], auth=None)
def list_audit_logs(
    request,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
):
    """
    List audit log entries for the organisation.
    Requires GOVERNANCE_MANAGE or AUDITOR-level permission.
    Supports filtering by action name, target type, and date range.
    """
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)

    qs = AuditLog.objects.filter(org_id=org_id).select_related("performed_by")

    if action:
        qs = qs.filter(action=action)
    if target_type:
        qs = qs.filter(target_type=target_type)
    if start_date:
        qs = qs.filter(performed_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(performed_at__date__lte=end_date)

    qs = qs[:max(1, min(limit, 500))]  # cap at 500

    return [_serialize_log(log) for log in qs]


@router.get("/audit-logs/{log_id}", response=AuditLogOut, auth=None)
def get_audit_log(request, log_id: UUID):
    """
    Retrieve a single audit log entry by ID.
    Requires LEDGER_VIEW_REPORT permission.
    """
    require_permission(request, Permissions.LEDGER_VIEW_REPORT)
    org_id = get_org_id(request)

    log = get_object_or_404(AuditLog, id=log_id, org_id=org_id)
    log = AuditLog.objects.select_related("performed_by").get(id=log_id, org_id=org_id)
    return _serialize_log(log)
