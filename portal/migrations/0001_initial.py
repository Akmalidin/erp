from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('crm', '0006_client_portal'),
        ('orders', '0006_order_discount_orderitem_discount_percent'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author_type', models.CharField(choices=[('client', 'Клиент'), ('admin', 'Менеджер')], default='client', max_length=10, verbose_name='Автор')),
                ('text', models.TextField(verbose_name='Текст заметки')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_notes', to='crm.client')),
                ('item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='portal_notes', to='orders.orderitem', verbose_name='Позиция')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='portal_notes', to='orders.order', verbose_name='Заказ')),
            ],
            options={
                'verbose_name': 'Заметка к заказу',
                'verbose_name_plural': 'Заметки к заказам',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='PortalNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=500, verbose_name='Текст')),
                ('url', models.CharField(blank=True, max_length=200, verbose_name='Ссылка')),
                ('is_read', models.BooleanField(default=False, verbose_name='Прочитано')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='crm.client', verbose_name='Клиент')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='portal_notifications', to=settings.AUTH_USER_MODEL, verbose_name='Менеджер')),
            ],
            options={
                'verbose_name': 'Уведомление портала',
                'verbose_name_plural': 'Уведомления портала',
                'ordering': ['-created_at'],
            },
        ),
    ]
