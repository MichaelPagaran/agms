import uuid
from django.db import models



class DocumentType(models.TextChoices):
    RESOLUTION = 'RESOLUTION', 'Board Resolution'
    MINUTES = 'MINUTES', 'Meeting Minutes'
    BYLAW = 'BYLAW', 'Bylaws'
    # Financial Reports
    SOA = 'SOA', 'Statement of Account'
    FIN_OP = 'FIN_OP', 'Statement of Financial Operations'
    FIN_POS = 'FIN_POS', 'Statement of Financial Position'
    CASH_FLOW = 'CASH_FLOW', 'Statement of Cash Flows'
    FUND_BALANCE = 'FUND_BALANCE', 'Statement of Changes in Fund Balance'
    
    OTHER = 'OTHER', 'Other'


class RequestStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    GENERATED = 'GENERATED', 'Generated'


class GovernanceDocument(models.Model):
    """
    Tracks Board Resolutions, Meeting Minutes, and other governance docs.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    
    title = models.CharField(max_length=255)
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.RESOLUTION
    )
    document_date = models.DateField()
    file_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)
    
    uploaded_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-document_date']
        verbose_name = "Governance Document"
        verbose_name_plural = "Governance Documents"

    def __str__(self):
        return f"{self.document_type}: {self.title}"


class DocumentRequest(models.Model):
    """
    Tracks requests for transparency documents by homeowners/members.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    
    # Requestor info
    requestor = models.ForeignKey('identity.User', on_delete=models.CASCADE, related_name='document_requests')
    
    # Document details
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.SOA
    )
    purpose = models.TextField(help_text="Purpose of the request for transparency.")
    
    # Date range for the report (optional depending on report type)
    date_range_start = models.DateField(null=True, blank=True)
    date_range_end = models.DateField(null=True, blank=True)
    
    # Approval workflow
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING
    )
    approved_by = models.ForeignKey(
        'identity.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_requests'
    )
    rejection_reason = models.TextField(blank=True)
    
    # Output
    generated_file = models.URLField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Document Request"
        verbose_name_plural = "Document Requests"

    def __str__(self):
        return f"{self.document_type} requested by {self.requestor} ({self.status})"


class AuditLog(models.Model):
    """
    Simple audit trail for critical actions like deletion.
    Keeps a record of who did what and when.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    
    action = models.CharField(max_length=50, help_text="Action performed (e.g., DELETE_UNIT)")
    target_type = models.CharField(max_length=50, help_text="Type of object acted on (e.g., Unit)")
    target_id = models.UUIDField(help_text="ID of the object acted on")
    target_label = models.CharField(max_length=255, blank=True, help_text="Human-readable label of the object")
    
    # Metadata
    performed_by = models.ForeignKey(
        'identity.User', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='audit_logs'
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    context = models.JSONField(default=dict, blank=True, help_text="Additional context/metadata")

    class Meta:
        ordering = ['-performed_at']
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        return f"{self.action} on {self.target_type} by {self.performed_by}"
