import uuid
from django.db import models


class MembershipStatus(models.TextChoices):
    GOOD_STANDING = 'GOOD_STANDING', 'Good Standing'
    DELINQUENT = 'DELINQUENT', 'Delinquent'
    NON_MEMBER = 'NON_MEMBER', 'Non-Member'


class OccupancyStatus(models.TextChoices):
    INHABITED = 'INHABITED', 'Inhabited'
    VACANT = 'VACANT', 'Vacant'
    UNDER_CONSTRUCTION = 'UNDER_CONSTRUCTION', 'Under Construction'


class UnitCategory(models.TextChoices):
    UNIT = 'UNIT', 'Unit'
    INFRASTRUCTURE = 'INFRASTRUCTURE', 'Infrastructure'


class Unit(models.Model):
    """
    Represents a Lot/Block (Subdivision) or Unit/Floor (Condo).
    Uses generic level_1/level_2 for market portability.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)  # No FK - modular boundary
    
    # Generic identifiers
    section_identifier = models.CharField(max_length=50, help_text="Block or Floor")
    unit_identifier = models.CharField(max_length=50, help_text="Lot or Unit")
    location_name = models.CharField(max_length=100, help_text="Street or Building Name", blank=True)
    
    # Map Coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    category = models.CharField(
        max_length=20,
        choices=UnitCategory.choices,
        default=UnitCategory.UNIT
    )
    
    # Owner information
    owner_id = models.UUIDField(null=True, blank=True, db_index=True) # Linked to Identity User
    owner_name = models.CharField(max_length=255, blank=True, null=True)
    owner_email = models.EmailField(blank=True, null=True)
    owner_phone = models.CharField(max_length=20, blank=True, null=True)
    resident_name = models.CharField(max_length=255, blank=True, null=True, help_text="Main point of contact")
    
    # Status tracking (RA 9904 compliance)
    membership_status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.GOOD_STANDING
    )
    occupancy_status = models.CharField(
        max_length=20,
        choices=OccupancyStatus.choices,
        default=OccupancyStatus.INHABITED
    )
    
    # DHSUD fields
    dhsud_membership_date = models.DateField(null=True, blank=True)
    voter_eligible = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['section_identifier', 'unit_identifier']
        unique_together = ['org_id', 'section_identifier', 'unit_identifier', 'location_name']

    def __str__(self):
        return f"{self.location_name} - {self.section_identifier} {self.unit_identifier}"
    
    @property
    def full_label(self):
        return f"{self.location_name} {self.section_identifier} {self.unit_identifier}"
