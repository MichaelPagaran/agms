from ninja import Schema
from ninja.orm import create_schema
from uuid import UUID
from datetime import date, datetime
from typing import Optional, Any
from .models import DocumentRequest, RequestStatus, DocumentType

# Create Schema from Model automatically for standard fields
DocumentRequestOut = create_schema(
    DocumentRequest, 
    fields=['id', 'document_type', 'purpose', 'date_range_start', 'date_range_end', 'status', 'rejection_reason', 'generated_file', 'created_at']
)

class DocumentRequestIn(Schema):
    document_type: str
    purpose: str
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None

class RequestApprovalIn(Schema):
    approved: bool
    rejection_reason: Optional[str] = None


class AuditLogOut(Schema):
    id: UUID
    org_id: UUID
    action: str
    target_type: str
    target_id: UUID
    target_label: str
    performed_by_name: Optional[str] = None
    performed_at: datetime
    context: Any


class AuditLogFiltersIn(Schema):
    action: Optional[str] = None
    target_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
