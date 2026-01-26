from typing import List, Optional
from uuid import UUID
from datetime import date
from django.shortcuts import get_object_or_404
from django.db.models import Q
from ninja import Router
from ninja.security import django_auth

from apps.identity.models import User
from apps.identity.permissions import Permissions, get_user_permissions
from apps.core.task_service import TaskService
from .models import DocumentRequest, RequestStatus
from .dtos import DocumentRequestIn, DocumentRequestOut, RequestApprovalIn

router = Router(tags=["Governance"])

@router.post("/requests", response=DocumentRequestOut, auth=django_auth)
def create_request(request, payload: DocumentRequestIn):
    """
    Create a new document request.
    """
    user = request.user
    
    doc_request = DocumentRequest.objects.create(
        org_id=user.org_id,
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
    """
    List document requests. 
    Homeowners see only their own. Staff/Board/Admin see all for their org.
    """
    user = request.user
    perms = get_user_permissions(user)
    
    qs = DocumentRequest.objects.filter(org_id=user.org_id)
    
    # Filter by visibility
    if Permissions.GOVERNANCE_MANAGE_DOCS in perms:
        # Can see all requests
        pass
    else:
        # Can only see own requests
        qs = qs.filter(requestor=user)
        
    # Optional status filter
    if status:
        qs = qs.filter(status=status)
        
    return list(qs)

@router.post("/requests/{request_id}/approve", response=DocumentRequestOut, auth=django_auth)
def approve_request(request, request_id: UUID):
    """
    Approve a document request. Triggers generation.
    Requires GOVERNANCE_MANAGE_DOCS permission.
    """
    user = request.user
    perms = get_user_permissions(user)
    
    if Permissions.GOVERNANCE_MANAGE_DOCS not in perms:
        from ninja.errors import HttpError
        raise HttpError(403, "You do not have permission to approve requests.")
        
    doc_request = get_object_or_404(DocumentRequest, id=request_id, org_id=user.org_id)
    
    if doc_request.status != RequestStatus.PENDING:
         # Potentially allow re-approval if needed, but usually once decided it's done.
         # For now, let's assume valid only for PENDING.
         pass
         
    doc_request.status = RequestStatus.APPROVED
    doc_request.approved_by = user
    doc_request.save()
    
    # Trigger async task for PDF generation via TaskService abstraction
    TaskService.generate_document(doc_request.id)
    
    return doc_request

@router.post("/requests/{request_id}/reject", response=DocumentRequestOut, auth=django_auth)
def reject_request(request, request_id: UUID, payload: RequestApprovalIn):
    """
    Reject a document request with a reason.
    Requires GOVERNANCE_MANAGE_DOCS permission.
    """
    user = request.user
    perms = get_user_permissions(user)
    
    if Permissions.GOVERNANCE_MANAGE_DOCS not in perms:
        from ninja.errors import HttpError
        raise HttpError(403, "You do not have permission to reject requests.")
        
    doc_request = get_object_or_404(DocumentRequest, id=request_id, org_id=user.org_id)
    
    doc_request.status = RequestStatus.REJECTED
    doc_request.rejection_reason = payload.rejection_reason or "No reason provided."
    # Reset approval info if it was somehow set
    doc_request.approved_by = None
    doc_request.save()
    
    return doc_request
