import uuid
from django.db import models


class OCRProcessingStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PROCESSING = 'PROCESSING', 'Processing'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class OCRJob(models.Model):
    """
    Tracks OCR processing jobs for receipt scanning.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    
    image_url = models.URLField()
    status = models.CharField(
        max_length=20,
        choices=OCRProcessingStatus.choices,
        default=OCRProcessingStatus.PENDING
    )
    
    # Extracted data
    extracted_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    extracted_date = models.DateField(null=True, blank=True)
    extracted_merchant = models.CharField(max_length=255, blank=True)
    raw_text = models.TextField(blank=True)
    
    created_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "OCR Job"
        verbose_name_plural = "OCR Jobs"

    def __str__(self):
        return f"OCR Job {self.id} - {self.status}"
