"""
Desktop sync models.
SyncState — последнее время синхронизации.
SyncLog   — журнал операций для conflict-resolution по времени.
"""
from django.db import models
from django.utils import timezone


class SyncState(models.Model):
    """Одна запись: текущий режим и время последней синхронизации."""
    db_mode   = models.CharField('Режим БД', max_length=10, default='sqlite')  # sqlite | postgres
    last_sync = models.DateTimeField('Последняя синхронизация', null=True, blank=True)
    syncing   = models.BooleanField('Синхронизация идёт', default=False)

    class Meta:
        verbose_name = 'Состояние синхронизации'

    def __str__(self):
        return f'{self.db_mode} / {self.last_sync}'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SyncLog(models.Model):
    """
    Журнал операций в SQLite-режиме.
    При синхронизации применяем к PostgreSQL в порядке timestamp.
    Конфликт: если тот же (app, model, object_id) изменён в обеих БД —
    побеждает запись с более поздним timestamp.
    """
    OP_CREATE = 'create'
    OP_UPDATE = 'update'
    OP_DELETE = 'delete'
    OP_CHOICES = [
        (OP_CREATE, 'Создание'),
        (OP_UPDATE, 'Изменение'),
        (OP_DELETE, 'Удаление'),
    ]

    app_label  = models.CharField('Приложение', max_length=50)
    model_name = models.CharField('Модель', max_length=100)
    object_id  = models.IntegerField('ID объекта')
    operation  = models.CharField('Операция', max_length=10, choices=OP_CHOICES)
    data_json  = models.TextField('Данные JSON', blank=True)   # сериализованный объект
    timestamp  = models.DateTimeField('Время', default=timezone.now)
    synced     = models.BooleanField('Синхронизировано', default=False)

    class Meta:
        verbose_name = 'Запись журнала синхронизации'
        verbose_name_plural = 'Журнал синхронизации'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['synced', 'timestamp']),
            models.Index(fields=['app_label', 'model_name', 'object_id']),
        ]

    def __str__(self):
        return f'{self.operation} {self.app_label}.{self.model_name}#{self.object_id} @ {self.timestamp}'


class PendingImport(models.Model):
    """
    Офлайн-очередь загрузки прайсов.
    Когда нет интернета — импорт сохраняется здесь.
    При подключении — пакетная загрузка на сервер.
    """
    STATUS_PENDING = 'pending'
    STATUS_SYNCING = 'syncing'
    STATUS_DONE    = 'done'
    STATUS_ERROR   = 'error'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидает'),
        (STATUS_SYNCING, 'Загружается'),
        (STATUS_DONE,    'Готово'),
        (STATUS_ERROR,   'Ошибка'),
    ]

    user        = models.ForeignKey('users.User', on_delete=models.CASCADE)
    filename    = models.CharField('Файл', max_length=255)
    rows_json   = models.TextField('Данные строк JSON')
    created_at  = models.DateTimeField('Создан', default=timezone.now)
    status      = models.CharField('Статус', max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_msg   = models.TextField('Ошибка', blank=True)
    rows_total  = models.IntegerField('Строк всего', default=0)
    rows_done   = models.IntegerField('Строк загружено', default=0)

    class Meta:
        verbose_name = 'Офлайн-импорт'
        verbose_name_plural = 'Офлайн-импорты'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.filename} ({self.status})'
