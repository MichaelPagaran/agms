from django.contrib import admin
from .models import GovernanceDocument


@admin.register(GovernanceDocument)
class GovernanceDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'document_date', 'created_at']
    list_filter = ['document_type', 'document_date']
    search_fields = ['title', 'description']
