from django.contrib import admin
from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['name', 'asset_type', 'rental_rate', 'is_active']
    list_filter = ['asset_type', 'is_active']
    search_fields = ['name', 'description']
