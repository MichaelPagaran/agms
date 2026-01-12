import uuid
from django.db import models


class OrganizationType(models.TextChoices):
    SUBDIVISION = 'SUBDIVISION', 'Subdivision'
    CONDOMINIUM = 'CONDOMINIUM', 'Condominium'


class Organization(models.Model):
    """
    Represents a tenant (HOA/Condo Corporation).
    All data is isolated per organization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    org_type = models.CharField(
        max_length=20,
        choices=OrganizationType.choices,
        default=OrganizationType.SUBDIVISION
    )
    settings = models.JSONField(
        default=dict,
        help_text="Flexible metadata (e.g., label overrides for Condo vs Subdivision)"
    )
    logo = models.URLField(blank=True, null=True)
    tin = models.CharField(max_length=50, blank=True, null=True, verbose_name="TIN")
    dhsud_registration = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
