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


class InviteStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    ACCEPTED = 'ACCEPTED', 'Accepted'
    EXPIRED = 'EXPIRED', 'Expired'


class UserInvite(models.Model):
    """
    Stores invitations for new users (Homeowners/Staff).
    Ensures strict tenant isolation by binding the token to an org_id.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    
    email = models.EmailField(db_index=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.HOMEOWNER
    )
    
    # Pre-linking to a Unit (Optional)
    unit_id = models.UUIDField(null=True, blank=True)
    
    # Security
    token = models.CharField(max_length=255, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    
    status = models.CharField(
        max_length=20,
        choices=InviteStatus.choices,
        default=InviteStatus.PENDING
    )
    
    invited_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['org_id', 'email'] # One active invite per email per org

    def __str__(self):
        return f"Invite for {self.email} ({self.status})"
