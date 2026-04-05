from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0004_shift_expensecategory_expense'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='discount_percent',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Скидка применяется автоматически при создании заказа',
                max_digits=5,
                verbose_name='Персональная скидка (%)'
            ),
        ),
    ]
