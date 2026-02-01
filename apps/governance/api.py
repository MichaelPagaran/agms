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
        org_id=user.org_id_id,
        requestor=user,
        transform=None, # Assuming transform is correct in original, just adding placeholder context
        document_type=payload.document_type,
        purpose=payload.purpose,
        date_range_start=payload.date_range_start,
        date_range_end=payload.date_range_end,
        status=RequestStatus.PENDING
    )
    return doc_request

@router.get("/requests", response=List[DocumentRequestOut], auth=django_auth)
def list_requests(request, status: Optional[str] = None):
    # ...
    
    qs = DocumentRequest.objects.filter(org_id=user.org_id_id)
    
    # ...

@router.post("/requests/{request_id}/approve", response=DocumentRequestOut, auth=django_auth)
def approve_request(request, request_id: UUID):
    # ...
        
    doc_request = get_object_or_404(DocumentRequest, id=request_id, org_id=user.org_id_id)
    
    # ...

@router.post("/requests/{request_id}/reject", response=DocumentRequestOut, auth=django_auth)
def reject_request(request, request_id: UUID, payload: RequestApprovalIn):
    # ...
        
    doc_request = get_object_or_404(DocumentRequest, id=request_id, org_id=user.org_id_id)
    
    doc_request.status = RequestStatus.REJECTED
    doc_request.rejection_reason = payload.rejection_reason or "No reason provided."
    # Reset approval info if it was somehow set
    doc_request.approved_by = None
    doc_request.save()
    
    return doc_request
