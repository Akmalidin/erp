from django.contrib import admin
from .models import StockMovement


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'change', 'movement_type', 'note', 'created_at')
    list_filter = ('movement_type', 'created_at')
    search_fields = ('product__name', 'product__oem_number', 'note')
    readonly_fields = ('created_at',)
