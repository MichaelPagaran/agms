import uuid
from django.db import models


class AssetType(models.TextChoices):
    REVENUE = 'REVENUE', 'Revenue-Generating'
    SHARED = 'SHARED', 'Shared Infrastructure'


class Asset(models.Model):
    """
    Represents facilities (Pool, Clubhouse, Gates, etc.).
    Revenue facilities have rental rates; shared don't.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    
    name = models.CharField(max_length=255)
    asset_type = models.CharField(
        max_length=20,
        choices=AssetType.choices,
        default=AssetType.SHARED
    )
    description = models.TextField(blank=True)
    rental_rate = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Rental rate per use/hour (for revenue facilities)"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
