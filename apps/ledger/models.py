import uuid
from decimal import Decimal
from django.db import models


class TransactionType(models.TextChoices):
    INCOME = 'INCOME', 'Income'
    EXPENSE = 'EXPENSE', 'Expense'


class TransactionStatus(models.TextChoices):
    """Transaction approval workflow states."""
    DRAFT = 'DRAFT', 'Draft'
    PENDING = 'PENDING', 'Pending Verification'
    POSTED = 'POSTED', 'Posted'
    CANCELLED = 'CANCELLED', 'Cancelled'


class PaymentType(models.TextChoices):
    """Payment type for income transactions - critical for amount validation."""
    EXACT = 'EXACT', 'Exact Payment'
    ADVANCE = 'ADVANCE', 'Advance Payment'


class DiscountType(models.TextChoices):
    PERCENTAGE = 'PERCENTAGE', 'Percentage'
    FLAT = 'FLAT', 'Flat Amount'


class AdjustmentType(models.TextChoices):
    DISCOUNT = 'DISCOUNT', 'Discount'
    PENALTY = 'PENALTY', 'Penalty'


class CreditTransactionType(models.TextChoices):
    """Types of credit balance changes."""
    DEPOSIT = 'DEPOSIT', 'Deposit (Advance Payment)'
    DUES_DEDUCTION = 'DUES_DEDUCTION', 'Dues Deduction'
    REFUND = 'REFUND', 'Refund'
    ADJUSTMENT = 'ADJUSTMENT', 'Manual Adjustment'


class DuesStatementStatus(models.TextChoices):
    """Status of monthly dues statements."""
    UNPAID = 'UNPAID', 'Unpaid'
    PARTIAL = 'PARTIAL', 'Partially Paid'
    PAID = 'PAID', 'Paid'
    OVERDUE = 'OVERDUE', 'Overdue'
    WAIVED = 'WAIVED', 'Waived'


class TransactionCategory(models.Model):
    """
    Configurable transaction categories per organization.
    Allows HOAs to customize their income/expense categories.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    
    name = models.CharField(max_length=100)
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices
    )
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False, help_text="System-generated default category")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ['org_id', 'name', 'transaction_type']
        verbose_name = "Transaction Category"
        verbose_name_plural = "Transaction Categories"

    def __str__(self):
        return f"{self.name} ({self.transaction_type})"


class Transaction(models.Model):
    """
    Records income and expenses.
    Uses UUID references instead of FKs for modular boundaries.
    Includes approval workflow and payment type validation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)  # Organization reference
    unit_id = models.UUIDField(null=True, blank=True, db_index=True)  # Unit reference (optional)
    asset_id = models.UUIDField(null=True, blank=True, db_index=True)  # Asset reference (optional)
    category_id = models.UUIDField(null=True, blank=True, db_index=True)  # TransactionCategory reference
    
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices
    )
    
    # Approval workflow
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.POSTED
    )
    
    # Payment type - critical for amount validation
    payment_type = models.CharField(
        max_length=10,
        choices=PaymentType.choices,
        default=PaymentType.EXACT,
        help_text="EXACT requires amount to match dues; ADVANCE allows overpayment to credit"
    )
    
    # Amount fields
    gross_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Amount before adjustments"
    )
    net_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Final amount after discounts/penalties"
    )
    
    # Legacy field for backward compatibility
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    category = models.CharField(max_length=100)  # Legacy field, use category_id
    description = models.TextField(blank=True)
    payer_name = models.CharField(max_length=255, blank=True, null=True)
    reference_number = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="External reference (OR number, check number, etc.)"
    )
    receipt_image = models.URLField(blank=True, null=True)  # Legacy field
    
    # Receipt requirement
    requires_receipt = models.BooleanField(default=False)
    receipt_verified = models.BooleanField(default=False)
    
    # Verification (Audit)
    is_verified = models.BooleanField(default=False, help_text="Checked and verified by board/admin")
    verified_by_id = models.UUIDField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Accounts Payable Tracking
    is_disbursed = models.BooleanField(
        default=True,
        help_text="True if cash has left the organization. False means Account Payable."
    )
    disbursement_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Date when payment was actually made (if different from transaction date)"
    )
    
    # Dates
    transaction_date = models.DateField()
    
    # Audit fields
    created_by_id = models.UUIDField(null=True, blank=True)  # User reference
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f"{self.transaction_type} - {self.net_amount} ({self.category})"
    
    def save(self, *args, **kwargs):
        # Ensure amount field stays in sync with net_amount for backward compatibility
        if self.net_amount:
            self.amount = self.net_amount
        super().save(*args, **kwargs)


class TransactionAttachment(models.Model):
    """
    Stores receipt/document attachments for transactions.
    Currently for evidence only; AI OCR integration planned for future.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_id = models.UUIDField(db_index=True)  # Transaction reference
    
    file_url = models.URLField(help_text="URL to the uploaded file (S3 or local)")
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(
        max_length=50,
        help_text="MIME type (image/jpeg, image/png, application/pdf)"
    )
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    
    uploaded_by_id = models.UUIDField(null=True, blank=True)  # User reference
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transaction Attachment"
        verbose_name_plural = "Transaction Attachments"

    def __str__(self):
        return f"Attachment for {self.transaction_id}: {self.file_name}"


class TransactionAdjustment(models.Model):
    """
    Records applied discounts or penalties on a transaction.
    Penalty amounts use Simple Interest calculation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_id = models.UUIDField(db_index=True)  # Transaction reference
    
    adjustment_type = models.CharField(
        max_length=10,
        choices=AdjustmentType.choices
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Positive for discounts/penalties (applied to gross)"
    )
    reason = models.CharField(max_length=255)
    
    # For penalties: store calculation details
    penalty_months = models.PositiveSmallIntegerField(
        null=True, 
        blank=True,
        help_text="Number of months overdue (for penalty calculation)"
    )
    penalty_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=4,
        null=True, 
        blank=True,
        help_text="Interest rate used (e.g., 0.02 for 2%)"
    )
    
    created_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transaction Adjustment"
        verbose_name_plural = "Transaction Adjustments"

    def __str__(self):
        sign = "-" if self.adjustment_type == AdjustmentType.DISCOUNT else "+"
        return f"{sign}{self.amount} ({self.adjustment_type}): {self.reason}"


class DiscountConfig(models.Model):
    """
    Organization discount policies.
    Supports percentage or flat amount discounts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    
    name = models.CharField(max_length=100, help_text="e.g., 'Early Payment Discount', '12-Month Advance Discount'")
    description = models.TextField(blank=True)
    
    discount_type = models.CharField(
        max_length=10,
        choices=DiscountType.choices
    )
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Percentage (e.g., 20.00 for 20%) or flat amount"
    )
    
    # Applicability
    applicable_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="List of category IDs this discount applies to (empty = all)"
    )
    min_months = models.PositiveSmallIntegerField(
        default=1,
        help_text="Minimum months for bulk payment discount (e.g., 12 for yearly)"
    )
    
    # Validity
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Discount Configuration"
        verbose_name_plural = "Discount Configurations"

    def __str__(self):
        if self.discount_type == DiscountType.PERCENTAGE:
            return f"{self.name}: {self.value}%"
        return f"{self.name}: ₱{self.value}"


class PenaltyPolicy(models.Model):
    """
    Organization penalty/interest policies.
    Uses Simple Interest calculation only (no compound interest).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    
    name = models.CharField(max_length=100, help_text="e.g., 'Late Payment Penalty'")
    description = models.TextField(blank=True)
    
    rate_type = models.CharField(
        max_length=10,
        choices=[('FLAT', 'Flat Fee'), ('PERCENT', 'Percentage')],
        default='PERCENT'
    )
    rate_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Rate value (e.g., 2.00 for 2% or flat amount)"
    )
    
    # Calculation method - ALWAYS Simple Interest
    CALCULATION_METHOD = 'SIMPLE_INTEREST'
    
    grace_period_days = models.PositiveSmallIntegerField(
        default=15,
        help_text="Days after due date before penalty applies"
    )
    
    # Applicability
    applicable_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="List of category IDs this penalty applies to (empty = all)"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Penalty Policy"
        verbose_name_plural = "Penalty Policies"

    def __str__(self):
        if self.rate_type == 'PERCENT':
            return f"{self.name}: {self.rate_value}% (Simple Interest)"
        return f"{self.name}: ₱{self.rate_value} flat"
    
    def calculate_penalty(self, principal: Decimal, months_overdue: int) -> Decimal:
        """
        Calculate penalty using Simple Interest: I = P × R × T
        
        Args:
            principal: The unpaid dues amount
            months_overdue: Number of months overdue
            
        Returns:
            Decimal: The penalty amount
        """
        if self.rate_type == 'FLAT':
            return self.rate_value * months_overdue
        else:
            # Simple Interest: I = P × R × T
            rate = self.rate_value / Decimal('100')  # Convert percentage to decimal
            return principal * rate * months_overdue


class BillingConfig(models.Model):
    """
    Organization billing configuration.
    Defines monthly dues amount, billing day, and grace period.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(unique=True, db_index=True)
    
    monthly_dues_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Base monthly dues amount per unit"
    )
    billing_day = models.PositiveSmallIntegerField(
        default=1,
        help_text="Day of month to generate statements (1-28)"
    )
    grace_period_days = models.PositiveSmallIntegerField(
        default=15,
        help_text="Days after due date before penalties apply"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Billing Configuration"
        verbose_name_plural = "Billing Configurations"

    def __str__(self):
        return f"Billing Config - ₱{self.monthly_dues_amount}/month (Day {self.billing_day})"


class DuesStatement(models.Model):
    """
    Monthly dues tracking per unit.
    Tracks base amount, penalties, discounts, and payment status.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    unit_id = models.UUIDField(db_index=True)
    
    # Statement period
    statement_month = models.PositiveSmallIntegerField(help_text="Month (1-12)")
    statement_year = models.PositiveSmallIntegerField(help_text="Year")
    
    # Amounts
    base_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Original dues amount"
    )
    penalty_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total penalties applied"
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total discounts applied"
    )
    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Final amount due (base + penalty - discount)"
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount already paid"
    )
    
    # Status and dates
    status = models.CharField(
        max_length=20,
        choices=DuesStatementStatus.choices,
        default=DuesStatementStatus.UNPAID
    )
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    
    # Linked transaction
    payment_transaction_id = models.UUIDField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-statement_year', '-statement_month']
        unique_together = ['org_id', 'unit_id', 'statement_year', 'statement_month']
        verbose_name = "Dues Statement"
        verbose_name_plural = "Dues Statements"

    def __str__(self):
        return f"Dues {self.statement_month}/{self.statement_year} - Unit {self.unit_id}"
    
    @property
    def balance_due(self) -> Decimal:
        """Returns remaining balance to be paid."""
        return self.net_amount - self.amount_paid


class UnitCredit(models.Model):
    """
    Advance payment credit system.
    Stores the current credit balance for a unit from advance payments.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.UUIDField(db_index=True)
    unit_id = models.UUIDField(db_index=True, unique=True)  # One credit account per unit
    
    credit_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current available credit from advance payments"
    )
    
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Unit Credit"
        verbose_name_plural = "Unit Credits"

    def __str__(self):
        return f"Credit for Unit {self.unit_id}: ₱{self.credit_balance}"


class CreditTransaction(models.Model):
    """
    Credit ledger for audit trail.
    Records all changes to a unit's credit balance.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit_credit_id = models.UUIDField(db_index=True)  # UnitCredit reference
    transaction_id = models.UUIDField(
        null=True, 
        blank=True,
        db_index=True,
        help_text="Linked payment transaction (if applicable)"
    )
    
    transaction_type = models.CharField(
        max_length=20,
        choices=CreditTransactionType.choices
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Positive for deposits, negative for deductions"
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Credit balance after this transaction"
    )
    
    description = models.CharField(max_length=255, blank=True)
    
    created_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Credit Transaction"
        verbose_name_plural = "Credit Transactions"

    def __str__(self):
        sign = "+" if self.amount > 0 else ""
        return f"{sign}{self.amount} ({self.transaction_type})"
