# Generated manually for ImportHistory model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0004_carmake_carmodel_product_compatible_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='ImportHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=255, verbose_name='Имя файла')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата импорта')),
                ('total_rows', models.PositiveIntegerField(verbose_name='Всего строк')),
                ('created_count', models.PositiveIntegerField(default=0, verbose_name='Создано')),
                ('updated_count', models.PositiveIntegerField(default=0, verbose_name='Обновлено')),
                ('errors_count', models.PositiveIntegerField(default=0, verbose_name='Ошибок')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.user')),
            ],
            options={
                'verbose_name': 'История импорта',
                'verbose_name_plural': 'Истории импортов',
                'ordering': ['-created_at'],
            },
        ),
    ]