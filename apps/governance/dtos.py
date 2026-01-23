from ninja import Schema
from ninja.orm import create_schema
from uuid import UUID
from datetime import date
from typing import Optional
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
