from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('total',)

    def total(self, obj):
        return obj.total
    total.short_description = 'Сумма'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('pk', 'client', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('client__name', 'pk')
    inlines = [OrderItemInline]
