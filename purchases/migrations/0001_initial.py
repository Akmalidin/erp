# Generated migration for purchases app
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('catalog', '0004_carmake_carmodel_product_compatible_models'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название')),
                ('contact_name', models.CharField(blank=True, max_length=255, verbose_name='Контактное лицо')),
                ('phone', models.CharField(blank=True, max_length=30, verbose_name='Телефон')),
                ('email', models.EmailField(blank=True, verbose_name='Email')),
                ('address', models.TextField(blank=True, verbose_name='Адрес')),
                ('notes', models.TextField(blank=True, verbose_name='Заметки')),
                ('debt', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Долг перед поставщиком')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлен')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='suppliers', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Поставщик',
                'verbose_name_plural': 'Поставщики',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='PurchaseOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_number', models.CharField(blank=True, max_length=100, verbose_name='Номер накладной')),
                ('status', models.CharField(choices=[('draft', 'Черновик'), ('confirmed', 'Проведена'), ('cancelled', 'Отменена')], default='draft', max_length=20, verbose_name='Статус')),
                ('total_price', models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='Сумма')),
                ('paid_amount', models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='Оплачено')),
                ('notes', models.TextField(blank=True, verbose_name='Примечание')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлена')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purchase_orders', to=settings.AUTH_USER_MODEL)),
                ('supplier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='purchases.supplier', verbose_name='Поставщик')),
            ],
            options={
                'verbose_name': 'Закупка',
                'verbose_name_plural': 'Закупки',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PurchaseItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Кол-во')),
                ('price', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Закупочная цена за ед.')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='purchases.purchaseorder', verbose_name='Закупка')),
                ('product', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='purchase_items', to='catalog.product', verbose_name='Товар')),
            ],
            options={
                'verbose_name': 'Позиция закупки',
                'verbose_name_plural': 'Позиции закупки',
            },
        ),
    ]
