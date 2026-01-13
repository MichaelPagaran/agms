from django.contrib import admin
from .models import (
    TransactionCategory,
    Transaction,
    TransactionAttachment,
    TransactionAdjustment,
    DiscountConfig,
    PenaltyPolicy,
    PenaltyConfig,
    DuesStatement,
    UnitCredit,
    CreditTransaction,
)


@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'transaction_type', 'org_id', 'is_active', 'is_default']
    list_filter = ['transaction_type', 'is_active', 'is_default']
    search_fields = ['name', 'description']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'transaction_type', 'status', 'net_amount', 'category', 'transaction_date', 'org_id']
    list_filter = ['transaction_type', 'status', 'payment_type', 'transaction_date']
    search_fields = ['description', 'payer_name', 'reference_number']
    date_hierarchy = 'transaction_date'
    readonly_fields = ['created_at', 'updated_at', 'approved_at']


@admin.register(TransactionAttachment)
class TransactionAttachmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'transaction_id', 'file_name', 'file_type', 'created_at']
    search_fields = ['file_name']
    readonly_fields = ['created_at']


@admin.register(TransactionAdjustment)
class TransactionAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'transaction_id', 'adjustment_type', 'amount', 'reason', 'created_at']
    list_filter = ['adjustment_type']
    search_fields = ['reason']
    readonly_fields = ['created_at']


@admin.register(DiscountConfig)
class DiscountConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'discount_type', 'value', 'min_months', 'is_active', 'org_id']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['name', 'description']


@admin.register(PenaltyPolicy)
class PenaltyPolicyAdmin(admin.ModelAdmin):
    list_display = ['name', 'rate_type', 'rate_value', 'grace_period_days', 'is_active', 'org_id']
    list_filter = ['rate_type', 'is_active']
    search_fields = ['name', 'description']


@admin.register(PenaltyConfig)
class PenaltyConfigAdmin(admin.ModelAdmin):
    list_display = ['org_id', 'monthly_due_rate', 'due_day', 'late_penalty_rate', 'is_active']
    list_filter = ['is_active']


@admin.register(DuesStatement)
class DuesStatementAdmin(admin.ModelAdmin):
    list_display = ['unit_id', 'statement_month', 'statement_year', 'net_amount', 'status', 'due_date']
    list_filter = ['status', 'statement_year', 'statement_month']
    search_fields = ['unit_id']
    date_hierarchy = 'due_date'


@admin.register(UnitCredit)
class UnitCreditAdmin(admin.ModelAdmin):
    list_display = ['unit_id', 'credit_balance', 'last_updated', 'org_id']
    search_fields = ['unit_id']
    readonly_fields = ['last_updated', 'created_at']


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'unit_credit_id', 'transaction_type', 'amount', 'balance_after', 'created_at']
    list_filter = ['transaction_type']
    search_fields = ['description']
    readonly_fields = ['created_at']
