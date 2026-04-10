from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0006_client_portal'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='sync_id',
            field=models.UUIDField(blank=True, db_index=True, null=True, unique=True, verbose_name='Sync ID'),
        ),
    ]
