"""
Supplier and Purchase Order models for procurement management.
"""
from decimal import Decimal
from django.db import models
from django.conf import settings
from catalog.models import Product


class Supplier(models.Model):
    """Vendor / supplier from whom we purchase parts."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='suppliers')
    name = models.CharField('Название', max_length=255)
    contact_name = models.CharField('Контактное лицо', max_length=255, blank=True)
    phone = models.CharField('Телефон', max_length=30, blank=True)
    email = models.EmailField('Email', blank=True)
    address = models.TextField('Адрес', blank=True)
    notes = models.TextField('Заметки', blank=True)
    debt = models.DecimalField('Долг перед поставщиком', max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        ordering = ['name']

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    """Incoming goods delivery / purchase invoice from a supplier."""

    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('confirmed', 'Проведена'),
        ('cancelled', 'Отменена'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='purchase_orders'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Поставщик',
        related_name='orders'
    )
    invoice_number = models.CharField('Номер накладной', max_length=100, blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='draft')
    total_price = models.DecimalField('Сумма', max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField('Оплачено', max_digits=14, decimal_places=2, default=0)
    notes = models.TextField('Примечание', blank=True)
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)

    class Meta:
        verbose_name = 'Закупка'
        verbose_name_plural = 'Закупки'
        ordering = ['-created_at']

    def __str__(self):
        supplier_name = self.supplier.name if self.supplier else 'Без поставщика'
        return f'Закупка #{self.pk} — {supplier_name}'

    @property
    def debt(self):
        return max(self.total_price - self.paid_amount, Decimal('0'))

    @property
    def status_color(self):
        return {'draft': '#f59e0b', 'confirmed': '#10b981', 'cancelled': '#ef4444'}.get(self.status, '#6b7280')


class PurchaseItem(models.Model):
    """Line item in a purchase order."""
    order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Закупка'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Товар',
        related_name='purchase_items'
    )
    quantity = models.PositiveIntegerField('Кол-во', default=1)
    price = models.DecimalField('Закупочная цена за ед.', max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'Позиция закупки'
        verbose_name_plural = 'Позиции закупки'

    def __str__(self):
        name = self.product.name if self.product else '?'
        return f'{name} x{self.quantity}'

    @property
    def total(self):
        return self.quantity * self.price
