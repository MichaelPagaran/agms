import uuid
from decimal import Decimal
from django.db import models


class TransactionType(models.TextChoices):
    INCOME = 'INCOME', 'Income'
    EXPENSE = 'EXPENSE', 'Expense'


class Transaction(models.Model):
    """
    Records income and expenses.
    Uses UUID references instead of FKs for modular boundaries.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)  # Organization reference
    unit_id = models.UUIDField(null=True, blank=True, db_index=True)  # Unit reference (optional)
    asset_id = models.UUIDField(null=True, blank=True, db_index=True)  # Asset reference (optional)
    
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    receipt_image = models.URLField(blank=True, null=True)
    
    transaction_date = models.DateField()
    created_by_id = models.UUIDField(null=True, blank=True)  # User reference
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} ({self.category})"


class PenaltyConfig(models.Model):
    """
    Stores HOA-specific penalty/interest rates (per RA 9904 bylaws).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    
    monthly_due_rate = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Monthly dues amount (flat) or rate per sqm"
    )
    due_day = models.PositiveSmallIntegerField(default=5, help_text="Day of month dues are due")
    grace_period_days = models.PositiveSmallIntegerField(default=15)
    late_penalty_type = models.CharField(
        max_length=20,
        choices=[('FLAT', 'Flat Fee'), ('PERCENT', 'Percentage')],
        default='PERCENT'
    )
    late_penalty_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('2.00'),
        help_text="Penalty rate (e.g., 2.00 for 2%)"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Penalty Configuration"
        verbose_name_plural = "Penalty Configurations"

    def __str__(self):
        return f"Penalty Config - Org {self.org_id}"
