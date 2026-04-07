"""
Product, Category, and PriceLevel models for auto parts catalog.
"""
from decimal import Decimal
from django.db import models


class CarMake(models.Model):
    """Vehicle manufacturer (Toyota, BMW, etc)."""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='car_makes')
    name = models.CharField('Марка', max_length=100)

    class Meta:
        verbose_name = 'Марка авто'
        verbose_name_plural = 'Марки авто'
        ordering = ['name']

    def __str__(self):
        return self.name


class CarModel(models.Model):
    """Vehicle model (Camry, X5, etc)."""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='car_models')
    make = models.ForeignKey(CarMake, on_delete=models.CASCADE, related_name='models', verbose_name='Марка')
    name = models.CharField('Модель', max_length=100)

    class Meta:
        verbose_name = 'Модель авто'
        verbose_name_plural = 'Модели авто'
        ordering = ['make__name', 'name']

    def __str__(self):
        return f'{self.make.name} {self.name}'


class Category(models.Model):
    """Product category for organizing parts."""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='categories')
    name = models.CharField('Название', max_length=255)
    description = models.TextField('Описание', blank=True)
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class PriceLevel(models.Model):
    """
    Configurable markup level. Each level defines a markup percentage
    applied to the purchase price to calculate the selling price.
    Example: Розничная +30%, Мелкий опт +20%, Опт +15%, Дилер +10%
    """
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='price_levels')
    name = models.CharField('Название', max_length=100)
    markup_percent = models.DecimalField(
        'Наценка (%)',
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text='Процент наценки на закупочную цену'
    )
    order = models.IntegerField('Порядок', default=0, help_text='Порядок отображения')
    is_default = models.BooleanField(
        'По умолчанию',
        default=False,
        help_text='Цена по умолчанию для новых заказов'
    )
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Уровень цены'
        verbose_name_plural = 'Уровни цен'
        ordering = ['order', 'name']

    def __str__(self):
        return f'{self.name} (+{self.markup_percent}%)'

    def calculate_price(self, purchase_price):
        """Calculate selling price from purchase price + markup."""
        if not purchase_price:
            return Decimal('0.00')
        price = Decimal(str(purchase_price))
        markup = Decimal(str(self.markup_percent))
        return (price * (1 + markup / 100)).quantize(Decimal('0.01'))

    @classmethod
    def get_default(cls, user):
        """Get the default price level."""
        return cls.objects.filter(user=user, is_default=True).first() or cls.objects.filter(user=user).first()

    @classmethod
    def create_defaults(cls, user):
        """Create default price levels if none exist."""
        if cls.objects.filter(user=user).exists():
            return
        defaults = [
            {'name': 'Розничная', 'markup_percent': 30, 'order': 1, 'is_default': True},
            {'name': 'Мелкий опт', 'markup_percent': 20, 'order': 2, 'is_default': False},
            {'name': 'Опт', 'markup_percent': 15, 'order': 3, 'is_default': False},
            {'name': 'Дилер', 'markup_percent': 10, 'order': 4, 'is_default': False},
        ]
        for d in defaults:
            cls.objects.create(user=user, **d)


class Product(models.Model):
    """Auto part product with OEM/part numbers and pricing."""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='products')
    oem_number = models.CharField('OEM номер', max_length=100, db_index=True)
    part_number = models.CharField('Артикул', max_length=100, blank=True, db_index=True)
    name = models.CharField('Название', max_length=500)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Категория',
        related_name='products'
    )
    brand = models.CharField('Бренд', max_length=200, blank=True)
    barcode = models.CharField('Штрихкод', max_length=255, blank=True, null=True, db_index=True)
    description = models.TextField('Описание', blank=True)
    compatible_models = models.ManyToManyField(
        CarModel,
        blank=True,
        verbose_name='Совместимые авто',
        related_name='products'
    )
    analogs = models.ManyToManyField(
        'self', 
        blank=True, 
        verbose_name='Аналоги/Кроссы', 
        symmetrical=True
    )
    price_purchase = models.DecimalField(
        'Закупочная цена',
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Цена из прайс-листа / цена закупки'
    )
    stock_quantity = models.IntegerField('Остаток', default=0)
    min_stock = models.IntegerField('Мин. остаток', default=0)
    location = models.CharField('Место хранения', max_length=100, blank=True)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.oem_number} — {self.name}'

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.min_stock

    def get_price(self, price_level=None):
        """Get the selling price for a given price level."""
        if price_level is None:
            price_level = PriceLevel.get_default(self.user)
        if price_level:
            return price_level.calculate_price(self.price_purchase)
        return self.price_purchase

    def get_all_prices(self):
        """Get selling prices for all price levels."""
        levels = PriceLevel.objects.filter(user=self.user)
        return [
            {
                'level': level,
                'price': level.calculate_price(self.price_purchase),
            }
            for level in levels
        ]

    @property
    def price_retail(self):
        """Backward-compatible: retail price (default markup)."""
        return self.get_price()


class ImportHistory(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    filename = models.CharField('Имя файла', max_length=255)
    created_at = models.DateTimeField('Дата импорта', auto_now_add=True)
    total_rows = models.PositiveIntegerField('Всего строк')
    created_count = models.PositiveIntegerField('Создано', default=0)
    updated_count = models.PositiveIntegerField('Обновлено', default=0)
    errors_count = models.PositiveIntegerField('Ошибок', default=0)
    rows_json = models.TextField('Данные строк', blank=True, default='')

    class Meta:
        verbose_name = 'История импорта'
        verbose_name_plural = 'Истории импортов'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.filename} - {self.created_at.strftime("%d.%m.%Y %H:%M")}'
