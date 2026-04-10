from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0008_pricehistory'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='simple_mode',
            field=models.BooleanField(default=False, verbose_name='Простой режим'),
        ),
        migrations.AddField(
            model_name='user',
            name='price_level',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='users',
                to='catalog.pricelevel',
                verbose_name='Уровень цен',
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('admin', 'Администратор'), ('manager', 'Менеджер'), ('employee', 'Сотрудник')],
                default='manager', max_length=20, verbose_name='Роль',
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, default='', max_length=254, unique=True, verbose_name='Email'),
        ),
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(blank=True, db_index=True, max_length=30, verbose_name='Телефон'),
        ),
    ]
