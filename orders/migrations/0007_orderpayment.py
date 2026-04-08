from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0006_order_discount_orderitem_discount_percent'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='Сумма')),
                ('method', models.CharField(choices=[('cash', 'Наличные'), ('card', 'Карта'), ('transfer', 'Перевод'), ('qr', 'QR (mBank)')], default='cash', max_length=20, verbose_name='Способ оплаты')),
                ('qr_photo', models.ImageField(blank=True, null=True, upload_to='payments/qr/', verbose_name='Фото QR/чека')),
                ('note', models.CharField(blank=True, max_length=300, verbose_name='Примечание')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='orders.order', verbose_name='Заказ')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.user', verbose_name='Менеджер')),
            ],
            options={
                'verbose_name': 'Платёж по заказу',
                'verbose_name_plural': 'Платежи по заказам',
                'ordering': ['-created_at'],
            },
        ),
    ]
