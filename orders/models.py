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

    def __str__(self):
        client_name = self.client.name if self.client else 'Без клиента'
        return f'Заказ #{self.pk} — {client_name}'

    def recalculate_total(self):
        """Recalculate total price from items."""
        total = sum(item.total for item in self.items.all())
        self.total_price = total
        self.save(update_fields=['total_price'])

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

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    def __str__(self):
        return f'{self.product.name} x{self.quantity}' if self.product else f'Товар x{self.quantity}'

    @property
    def total(self):
        return self.quantity * self.price
