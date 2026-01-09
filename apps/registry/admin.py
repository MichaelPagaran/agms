from django.contrib import admin
from .models import Unit


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['full_label', 'owner_name', 'membership_status', 'occupancy_status', 'is_active']
    list_filter = ['membership_status', 'occupancy_status', 'is_active']
    search_fields = ['level_1', 'level_2', 'owner_name', 'owner_email']
