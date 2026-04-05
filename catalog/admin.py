from django.contrib import admin
from .models import Product, Category, PriceLevel


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('oem_number', 'part_number', 'name', 'category', 'price_purchase', 'stock_quantity', 'is_active')
    list_filter = ('category', 'is_active', 'brand')
    search_fields = ('oem_number', 'part_number', 'name', 'brand')
    list_editable = ('price_purchase', 'stock_quantity', 'is_active')


@admin.register(PriceLevel)
class PriceLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'markup_percent', 'order', 'is_default')
    list_editable = ('markup_percent', 'order', 'is_default')
