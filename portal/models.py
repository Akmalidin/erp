"""
Portal models: notes on orders and notifications to admin.
"""
from django.db import models
from crm.models import Client
from orders.models import Order, OrderItem


class OrderNote(models.Model):
    """A note left by a client or admin on an order or specific item."""
    AUTHOR_CHOICES = [
        ('client', 'Клиент'),
        ('admin', 'Менеджер'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='portal_notes', verbose_name='Заказ')
    item = models.ForeignKey(
        OrderItem, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='portal_notes', verbose_name='Позиция'
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='order_notes')
    author_type = models.CharField('Автор', max_length=10, choices=AUTHOR_CHOICES, default='client')
    text = models.TextField('Текст заметки')
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Заметка к заказу'
        verbose_name_plural = 'Заметки к заказам'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.client.name} → Заказ #{self.order_id}: {self.text[:40]}'


class PortalNotification(models.Model):
    """Notification for admin when client performs a portal action."""
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='portal_notifications', verbose_name='Менеджер'
    )
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Клиент')
    text = models.CharField('Текст', max_length=500)
    url = models.CharField('Ссылка', max_length=200, blank=True)
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Уведомление портала'
        verbose_name_plural = 'Уведомления портала'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.client.name}: {self.text[:50]}'
