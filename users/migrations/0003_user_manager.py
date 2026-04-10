from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_user_employee_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='manager',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='employees',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Менеджер (для сотрудников)',
            ),
        ),
    ]
