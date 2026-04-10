from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0007_orderpayment'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='sync_id',
            field=models.UUIDField(blank=True, db_index=True, null=True, unique=True, verbose_name='Sync ID'),
        ),
    ]
