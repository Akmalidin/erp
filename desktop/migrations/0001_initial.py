from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SyncState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('db_mode', models.CharField(default='sqlite', max_length=10, verbose_name='Режим БД')),
                ('last_sync', models.DateTimeField(blank=True, null=True, verbose_name='Последняя синхронизация')),
                ('syncing', models.BooleanField(default=False, verbose_name='Синхронизация идёт')),
            ],
            options={
                'verbose_name': 'Состояние синхронизации',
            },
        ),
        migrations.CreateModel(
            name='SyncLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('app_label', models.CharField(max_length=50, verbose_name='Приложение')),
                ('model_name', models.CharField(max_length=100, verbose_name='Модель')),
                ('object_id', models.IntegerField(verbose_name='ID объекта')),
                ('operation', models.CharField(choices=[('create', 'Создание'), ('update', 'Изменение'), ('delete', 'Удаление')], max_length=10, verbose_name='Операция')),
                ('data_json', models.TextField(blank=True, verbose_name='Данные JSON')),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Время')),
                ('synced', models.BooleanField(default=False, verbose_name='Синхронизировано')),
            ],
            options={
                'verbose_name': 'Запись журнала синхронизации',
                'verbose_name_plural': 'Журнал синхронизации',
                'ordering': ['timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='synclog',
            index=models.Index(fields=['synced', 'timestamp'], name='desktop_syn_synced_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='synclog',
            index=models.Index(fields=['app_label', 'model_name', 'object_id'], name='desktop_syn_app_mod_obj_idx'),
        ),
        migrations.CreateModel(
            name='PendingImport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, to='users.user')),
                ('filename', models.CharField(max_length=255, verbose_name='Файл')),
                ('rows_json', models.TextField(verbose_name='Данные строк JSON')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Создан')),
                ('status', models.CharField(choices=[('pending', 'Ожидает'), ('syncing', 'Загружается'), ('done', 'Готово'), ('error', 'Ошибка')], default='pending', max_length=10, verbose_name='Статус')),
                ('error_msg', models.TextField(blank=True, verbose_name='Ошибка')),
                ('rows_total', models.IntegerField(default=0, verbose_name='Строк всего')),
                ('rows_done', models.IntegerField(default=0, verbose_name='Строк загружено')),
            ],
            options={
                'verbose_name': 'Офлайн-импорт',
                'verbose_name_plural': 'Офлайн-импорты',
                'ordering': ['-created_at'],
            },
        ),
    ]
