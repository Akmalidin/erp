from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_import_history'),
    ]

    operations = [
        migrations.AddField(
            model_name='importhistory',
            name='rows_json',
            field=models.TextField(blank=True, default='', verbose_name='Данные строк'),
        ),
    ]
