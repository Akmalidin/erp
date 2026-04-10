"""
Client model for CRM.
"""
from django.db import models


class Client(models.Model):
    """Client / customer record."""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='clients')
    name = models.CharField('ФИО / Название', max_length=255)
    phone = models.CharField('Телефон', max_length=30, blank=True)
    email = models.EmailField('Email', blank=True)
    company_name = models.CharField('Компания', max_length=255, blank=True)
    address = models.TextField('Адрес', blank=True)
    notes = models.TextField('Заметки', blank=True)
    discount_percent = models.DecimalField(
        'Персональная скидка (%)',
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Скидка применяется автоматически при создании заказа'
    )
    debt = models.DecimalField('Долг', max_digits=12, decimal_places=2, default=0.00)
    portal_enabled = models.BooleanField('Доступ к порталу', default=False)
    portal_password = models.CharField('Пароль портала', max_length=128, blank=True,
                                       help_text='Хранится в хешированном виде')
    sync_id = models.UUIDField('Sync ID', null=True, blank=True, unique=True, db_index=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        if self.company_name:
            return f'{self.name} ({self.company_name})'
        return self.name


class Payment(models.Model):
    """Record of a payment from a client."""
    PAYMENT_TYPES = [
        ('cash', 'Наличные'),
        ('card', 'Карта'),
        ('transfer', 'Перевод'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='payments')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField('Сумма', max_digits=12, decimal_places=2)
    payment_type = models.CharField('Способ оплаты', max_length=20, choices=PAYMENT_TYPES, default='cash')
    note = models.CharField('Примечание', max_length=255, blank=True)
    created_at = models.DateTimeField('Дата', auto_now_add=True)

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.client.name} — {self.amount}'


class ExpenseCategory(models.Model):
    """Category of business expenses (Rent, Salary, etc)."""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='expense_categories')
    name = models.CharField('Название', max_length=100)

    class Meta:
        verbose_name = 'Категория расхода'
        verbose_name_plural = 'Категории расходов'
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    """A business expense record."""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, verbose_name='Категория')
    amount = models.DecimalField('Сумма', max_digits=12, decimal_places=2)
    date = models.DateField('Дата', auto_now_add=True)
    note = models.CharField('Примечание', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Расход'
        verbose_name_plural = 'Расходы'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.category.name if self.category else "Без категории"} — {self.amount}'


class Shift(models.Model):
    """Cashier shift tracking (Z-report)."""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='shifts')
    opened_at = models.DateTimeField('Открыта', auto_now_add=True)
    closed_at = models.DateTimeField('Закрыта', null=True, blank=True)
    initial_cash = models.DecimalField('Начальная сумма в кассе', max_digits=12, decimal_places=2, default=0)
    
    # Financial results filled during closing
    actual_cash = models.DecimalField('Фактически наличных', max_digits=12, decimal_places=2, default=0)
    actual_card = models.DecimalField('Фактически по карте', max_digits=12, decimal_places=2, default=0)
    
    is_open = models.BooleanField('Открыта', default=True)

    class Meta:
        verbose_name = 'Смена'
        verbose_name_plural = 'Смены'
        ordering = ['-opened_at']

    def __str__(self):
        status = 'Открыта' if self.is_open else 'Закрыта'
        return f'Смена {self.id} — {status} ({self.opened_at.strftime("%d.%m %H:%M")})'
