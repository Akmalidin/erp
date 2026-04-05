"""
Stock movement tracking model.
"""
from django.db import models
from catalog.models import Product


class Warehouse(models.Model):
    """Physical storage location (Shop, Container, Main Warehouse etc)."""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='warehouses')
    name = models.CharField('Название склада', max_length=100)
    address = models.CharField('Адрес', max_length=255, blank=True)
    is_default = models.BooleanField('Основной', default=False)

    class Meta:
        verbose_name = 'Склад'
        verbose_name_plural = 'Склады'

    def __str__(self):
        return self.name

    @classmethod
    def get_default(cls, user):
        default = cls.objects.filter(user=user, is_default=True).first()
        if not default:
            default = cls.objects.filter(user=user).first()
        if not default:
            default = cls.objects.create(user=user, name='Основной склад', is_default=True)
        return default


class StockMovement(models.Model):
    """Tracks every change in product stock quantity."""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='stock_movements')

    MOVEMENT_TYPES = [
        ('sale', 'Продажа'),
        ('import', 'Поступление'),
        ('manual', 'Ручная корректировка'),
        ('return', 'Возврат'),
        ('transfer', 'Перемещение'),
    ]

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Склад',
        related_name='movements'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Товар',
        related_name='movements'
    )
    change = models.IntegerField('Изменение (+/-)')
    movement_type = models.CharField('Тип', max_length=20, choices=MOVEMENT_TYPES)
    note = models.TextField('Примечание', blank=True)
    created_at = models.DateTimeField('Дата', auto_now_add=True)

    class Meta:
        verbose_name = 'Движение товара'
        verbose_name_plural = 'Движения товаров'
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.change > 0 else ''
        return f'{self.product.name}: {sign}{self.change} ({self.get_movement_type_display()})'
