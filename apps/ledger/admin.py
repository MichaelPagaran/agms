from django.contrib import admin
from .models import Transaction, PenaltyConfig


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_type', 'amount', 'category', 'transaction_date', 'created_at']
    list_filter = ['transaction_type', 'category', 'transaction_date']
    search_fields = ['category', 'description']


@admin.register(PenaltyConfig)
class PenaltyConfigAdmin(admin.ModelAdmin):
    list_display = ['org_id', 'monthly_due_rate', 'due_day', 'late_penalty_rate', 'is_active']
    list_filter = ['is_active', 'late_penalty_type']
