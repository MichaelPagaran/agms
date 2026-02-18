from typing import List, Optional
from uuid import UUID
from datetime import date
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from ninja import Router
from ninja.security import django_auth
from ninja.errors import HttpError

from apps.identity.models import User
from apps.identity.permissions import Permissions, get_user_permissions
from apps.core.task_service import TaskService
from .models import DocumentRequest, RequestStatus
from .dtos import DocumentRequestIn, DocumentRequestOut, RequestApprovalIn

router = Router(tags=["Governance"])


def require_auth(request):
    """Require authenticated user."""
    if not request.user.is_authenticated:
        raise HttpError(401, "Authentication required")
    return request.user


@router.post("/requests", response=DocumentRequestOut, auth=django_auth)
def create_request(request, payload: DocumentRequestIn):
    """
    Create a new document request.
    """
    user = request.user
    
    doc_request = DocumentRequest.objects.create(
        org_id=user.org_id_id,
        requestor=user,
        document_type=payload.document_type,
        purpose=payload.purpose,
        date_range_start=payload.date_range_start,
        date_range_end=payload.date_range_end,
        status=RequestStatus.PENDING
    )
    return doc_request

@router.get("/requests", response=List[DocumentRequestOut], auth=django_auth)
def list_requests(request, status: Optional[str] = None):
    """List document requests for the user's organization."""
    user = request.user
    
    qs = DocumentRequest.objects.filter(org_id=user.org_id_id)
    
    if status:
        qs = qs.filter(status=status)
    
    return list(qs)

@router.post("/requests/{request_id}/approve", response=DocumentRequestOut, auth=django_auth)
def approve_request(request, request_id: UUID):
    """Approve a document request and trigger PDF generation."""
    user = request.user
        
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
    
    return doc_request

@router.post("/requests/{request_id}/reject", response=DocumentRequestOut, auth=django_auth)
def reject_request(request, request_id: UUID, payload: RequestApprovalIn):
    """Reject a document request."""
    user = request.user
        
    doc_request = get_object_or_404(DocumentRequest, id=request_id, org_id=user.org_id_id)
    
    if doc_request.status != RequestStatus.PENDING:
        raise HttpError(400, f"Cannot reject request with status '{doc_request.status}'")
    
    doc_request.status = RequestStatus.REJECTED
    doc_request.rejection_reason = payload.rejection_reason or "No reason provided."
    doc_request.approved_by = None
    doc_request.save()
    
    return doc_request

