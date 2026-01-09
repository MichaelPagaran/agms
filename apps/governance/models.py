import uuid
from django.db import models


class DocumentType(models.TextChoices):
    RESOLUTION = 'RESOLUTION', 'Board Resolution'
    MINUTES = 'MINUTES', 'Meeting Minutes'
    BYLAW = 'BYLAW', 'Bylaws'
    OTHER = 'OTHER', 'Other'


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
