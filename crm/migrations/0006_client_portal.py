from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0005_client_discount_percent'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='portal_enabled',
            field=models.BooleanField(default=False, verbose_name='Доступ к порталу'),
        ),
        migrations.AddField(
            model_name='client',
            name='portal_password',
            field=models.CharField(blank=True, help_text='Хранится в хешированном виде', max_length=128, verbose_name='Пароль портала'),
        ),
    ]
