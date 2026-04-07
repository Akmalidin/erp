from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0007_alter_importhistory_id'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PriceHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price_purchase', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Закупочная цена')),
                ('changed_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата изменения')),
                ('note', models.CharField(blank=True, max_length=255, verbose_name='Источник')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='price_history', to='catalog.product', verbose_name='Товар')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='price_history_records', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'История цен',
                'verbose_name_plural': 'История цен',
                'ordering': ['-changed_at'],
            },
        ),
    ]
