"""
Order and OrderItem models for sales management.
"""
from django.db import models
from django.conf import settings
from crm.models import Client
from catalog.models import Product


class Order(models.Model):
    """Sales order linked to a client."""

    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('processing', 'В обработке'),
        ('completed', 'Завершен'),
        ('returned', 'Возврат'),
        ('cancelled', 'Отменен'),
    ]

    DISCOUNT_TYPE_CHOICES = [
        ('none', 'Нет скидки'),
        ('percent', 'Процент (%)'),
        ('fixed', 'Фиксированная сумма'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Клиент',
        related_name='orders'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Создатель',
        related_name='orders'
    )
    total_price = models.DecimalField('Сумма', max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField('Оплачено', max_digits=14, decimal_places=2, default=0)
    payment_method = models.CharField('Способ оплаты', max_length=20, default='cash', choices=[
        ('cash', 'Наличные'),
        ('card', 'Карта'),
        ('mixed', 'Смешанная'),
        ('debt', 'В долг')
    ])
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')
    notes = models.TextField('Примечание', blank=True)
    discount_type = models.CharField('Тип скидки', max_length=10, default='none', choices=[
        ('none', 'Нет скидки'),
        ('percent', 'Процент (%)'),
        ('fixed', 'Фиксированная сумма'),
    ])
    discount_value = models.DecimalField('Скидка', max_digits=10, decimal_places=2, default=0)
    is_debt_recorded = models.BooleanField(default=False)
    shift = models.ForeignKey(
        'crm.Shift',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Смена',
        related_name='orders'
    )
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    @property
    def order_number(self):
        return f'INV-{self.pk:06d}'

    def __str__(self):
        client_name = self.client.name if self.client else 'Без клиента'
        return f'{self.order_number} — {client_name}'

    def recalculate_total(self):
        """Recalculate total price from items (with discounts)."""
        from decimal import Decimal
        subtotal = sum(item.total for item in self.items.all())
        if self.discount_type == 'percent' and self.discount_value:
            discount = subtotal * self.discount_value / Decimal('100')
        elif self.discount_type == 'fixed' and self.discount_value:
            discount = self.discount_value
        else:
            discount = Decimal('0')
        self.total_price = max(subtotal - discount, Decimal('0'))
        self.save(update_fields=['total_price'])

    @property
    def subtotal(self):
        return sum(item.total for item in self.items.all())

    @property
    def discount_amount(self):
        from decimal import Decimal
        sub = self.subtotal
        if self.discount_type == 'percent' and self.discount_value:
            return sub * self.discount_value / Decimal('100')
        elif self.discount_type == 'fixed' and self.discount_value:
            return self.discount_value
        return Decimal('0')

    @property
    def status_color(self):
        colors = {
            'new': '#3b82f6',
            'processing': '#f59e0b',
            'completed': '#10b981',
            'returned': '#8b5cf6',
            'cancelled': '#ef4444',
        }
        return colors.get(self.status, '#6b7280')

    @property
    def debt(self):
        return max(self.total_price - self.paid_amount, 0)


class OrderItem(models.Model):
    """Line item in an order."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name='Заказ',
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Товар',
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField('Кол-во', default=1)
    price = models.DecimalField('Цена за ед.', max_digits=12, decimal_places=2)
    discount_percent = models.DecimalField('Скидка (%)', max_digits=5, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    def __str__(self):
        return f'{self.product.name} x{self.quantity}' if self.product else f'Товар x{self.quantity}'

    @property
    def total(self):
        from decimal import Decimal
        base = self.quantity * self.price
        if self.discount_percent:
            return base * (1 - self.discount_percent / Decimal('100'))
        return base

    @property
    def discount_amount(self):
        from decimal import Decimal
        base = self.quantity * self.price
        if self.discount_percent:
            return base * self.discount_percent / Decimal('100')
        return Decimal('0')


class OrderPayment(models.Model):
    """Individual payment record for an order (supports QR photo upload)."""
    METHOD_CHOICES = [
        ('cash',     'Наличные'),
        ('card',     'Карта'),
        ('transfer', 'Перевод'),
        ('qr',       'QR (mBank)'),
    ]

    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments', verbose_name='Заказ')
    amount     = models.DecimalField('Сумма', max_digits=14, decimal_places=2)
    method     = models.CharField('Способ оплаты', max_length=20, choices=METHOD_CHOICES, default='cash')
    qr_photo   = models.ImageField('Фото QR/чека', upload_to='payments/qr/', blank=True, null=True)
    note       = models.CharField('Примечание', max_length=300, blank=True)
    created_at = models.DateTimeField('Дата', auto_now_add=True)
    user       = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, verbose_name='Менеджер'
    )

    class Meta:
        verbose_name = 'Платёж по заказу'
        verbose_name_plural = 'Платежи по заказам'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order.order_number}: {self.amount} ({self.method})'
