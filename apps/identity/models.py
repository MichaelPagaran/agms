import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrator'
    STAFF = 'STAFF', 'Staff'
    BOARD = 'BOARD', 'Board Member'
    AUDITOR = 'AUDITOR', 'Auditor'
    HOMEOWNER = 'HOMEOWNER', 'Home Owner'


class User(AbstractUser):
    """
    Custom User model with organization relationship for multi-tenancy.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Store org_id as UUID field (no FK to maintain app independence)
    org_id = models.UUIDField(null=True, blank=True, db_index=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.HOMEOWNER
    )
    phone = models.CharField(max_length=20, blank=True)
    
    class Meta:
        ordering = ['username']

    def __str__(self):
        return self.email or self.username
