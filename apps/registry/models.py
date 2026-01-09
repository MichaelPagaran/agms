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


class Unit(models.Model):
    """
    Represents a Lot/Block (Subdivision) or Unit/Floor (Condo).
    Uses generic level_1/level_2 for market portability.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)  # No FK - modular boundary
    
    # Generic identifiers (Block/Floor, Lot/Unit)
    level_1 = models.CharField(max_length=50, help_text="Block or Floor")
    level_2 = models.CharField(max_length=50, help_text="Lot or Unit")
    
    # Owner information
    owner_name = models.CharField(max_length=255)
    owner_email = models.EmailField(blank=True)
    owner_phone = models.CharField(max_length=20, blank=True)
    
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
        ordering = ['level_1', 'level_2']
        unique_together = ['org_id', 'level_1', 'level_2']

    def __str__(self):
        return f"{self.level_1} {self.level_2}"
    
    @property
    def full_label(self):
        return f"{self.level_1} {self.level_2}"
