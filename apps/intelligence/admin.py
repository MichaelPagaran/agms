from django.contrib import admin
from .models import OCRJob


@admin.register(OCRJob)
class OCRJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'extracted_total', 'extracted_date', 'created_at']
    list_filter = ['status']
    readonly_fields = ['id', 'created_at', 'completed_at']
