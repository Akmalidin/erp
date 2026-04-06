from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0005_order_shift'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='discount_type',
            field=models.CharField(
                choices=[('none', 'Нет скидки'), ('percent', 'Процент (%)'), ('fixed', 'Фиксированная сумма')],
                default='none',
                max_length=10,
                verbose_name='Тип скидки',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='discount_value',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Скидка'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='discount_percent',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='Скидка (%)'),
        ),
    ]
