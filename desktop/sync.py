"""
Движок синхронизации SQLite ↔ PostgreSQL.

Принцип:
  - Все изменения в офлайн-режиме пишутся в SyncLog (через сигналы).
  - При подключении:
      1. Читаем SyncLog где synced=False, сортируем по timestamp.
      2. Для каждой записи применяем к PostgreSQL.
      3. Конфликт: если тот же объект изменён в PostgreSQL после
         last_sync — сравниваем updated_at; побеждает более новый.
      4. Помечаем SyncLog.synced=True.
  - Тянем из PostgreSQL всё, что изменилось после last_sync (pull).
"""
import json
import logging
from datetime import timezone as dt_tz

import psycopg2
import psycopg2.extras
from django.apps import apps
from django.core import serializers
from django.utils import timezone

from .models import SyncLog, SyncState

logger = logging.getLogger('desktop.sync')

# Модели, которые синхронизируем (app_label.ModelName)
SYNC_MODELS = [
    'catalog.Product',
    'catalog.Category',
    'catalog.PriceLevel',
    'catalog.CarMake',
    'catalog.CarModel',
    'crm.Client',
    'orders.Order',
    'orders.OrderItem',
    'warehouse.Stock',
    'warehouse.StockMovement',
    'purchases.PurchaseOrder',
    'purchases.PurchaseItem',
]

PG_CONFIG = {
    'dbname':   'erp_db',
    'user':     'erp_user',
    'password': 'ErpPass2024',
    'host':     '46.149.68.65',
    'port':     '5432',
    'connect_timeout': 5,
}


def _pg_connect():
    return psycopg2.connect(**PG_CONFIG)


def get_model(app_label, model_name):
    return apps.get_model(app_label, model_name)


# ─────────────────────────────────────────────────────────────
# Сигналы: записывать изменения в SyncLog (только SQLite-режим)
# ─────────────────────────────────────────────────────────────

def register_signals():
    """Подключаем post_save / post_delete сигналы для всех sync-моделей."""
    import os
    if os.environ.get('DB_MODE', 'sqlite') != 'sqlite':
        return  # В PostgreSQL-режиме журнал не нужен

    from django.db.models.signals import post_save, post_delete

    for model_path in SYNC_MODELS:
        app_label, model_name = model_path.split('.')
        try:
            model = get_model(app_label, model_name)
        except LookupError:
            continue

        def make_save_handler(al, mn):
            def handler(sender, instance, created, **kwargs):
                _log_change(al, mn, instance, SyncLog.OP_CREATE if created else SyncLog.OP_UPDATE)
            return handler

        def make_delete_handler(al, mn):
            def handler(sender, instance, **kwargs):
                _log_change(al, mn, instance, SyncLog.OP_DELETE)
            return handler

        post_save.connect(make_save_handler(app_label, model_name), sender=model, weak=False)
        post_delete.connect(make_delete_handler(app_label, model_name), sender=model, weak=False)


def _log_change(app_label, model_name, instance, operation):
    try:
        data = ''
        if operation != SyncLog.OP_DELETE:
            data = serializers.serialize('json', [instance])
        SyncLog.objects.create(
            app_label=app_label,
            model_name=model_name,
            object_id=instance.pk,
            operation=operation,
            data_json=data,
        )
    except Exception as e:
        logger.warning(f'SyncLog write error: {e}')


# ─────────────────────────────────────────────────────────────
# PUSH: SQLite → PostgreSQL
# ─────────────────────────────────────────────────────────────

def push_to_postgres():
    """Применяем все несинхронизированные записи SyncLog к PostgreSQL."""
    pending = SyncLog.objects.filter(synced=False).order_by('timestamp')
    if not pending.exists():
        return 0, []

    errors = []
    count  = 0

    try:
        conn = _pg_connect()
        conn.autocommit = False
    except Exception as e:
        return 0, [f'Нет соединения с PostgreSQL: {e}']

    try:
        with conn:
            cur = conn.cursor()
            for log in pending:
                try:
                    _apply_log_to_pg(cur, log)
                    log.synced = True
                    log.save(update_fields=['synced'])
                    count += 1
                except Exception as e:
                    errors.append(f'{log}: {e}')
                    logger.error(f'Push error for {log}: {e}')
    finally:
        conn.close()

    return count, errors


def _apply_log_to_pg(cur, log: SyncLog):
    """Применяем одну запись SyncLog к открытому курсору PostgreSQL."""
    if log.operation == SyncLog.OP_DELETE:
        model = get_model(log.app_label, log.model_name)
        table = model._meta.db_table
        cur.execute(f'DELETE FROM {table} WHERE id = %s', [log.object_id])
        return

    if not log.data_json:
        return

    obj_list = json.loads(log.data_json)
    if not obj_list:
        return

    obj_data   = obj_list[0]
    model      = get_model(log.app_label, log.model_name)
    table      = model._meta.db_table
    fields     = obj_data['fields']

    # Разрешаем конфликт: смотрим updated_at в PostgreSQL
    if 'updated_at' in fields:
        cur.execute(f'SELECT updated_at FROM {table} WHERE id = %s', [log.object_id])
        row = cur.fetchone()
        if row and row[0]:
            pg_updated = row[0].replace(tzinfo=dt_tz.utc)
            local_updated_str = fields['updated_at']
            if local_updated_str:
                from django.utils.dateparse import parse_datetime
                local_updated = parse_datetime(local_updated_str)
                if local_updated and local_updated.replace(tzinfo=dt_tz.utc) <= pg_updated:
                    # PostgreSQL запись новее — пропускаем
                    return

    cols = list(fields.keys()) + ['id']
    vals = list(fields.values()) + [log.object_id]

    placeholders = ', '.join(['%s'] * len(cols))
    assignments  = ', '.join(f'{c} = EXCLUDED.{c}' for c in fields.keys())
    sql = (
        f'INSERT INTO {table} ({", ".join(cols)}) VALUES ({placeholders}) '
        f'ON CONFLICT (id) DO UPDATE SET {assignments}'
    )
    cur.execute(sql, vals)


# ─────────────────────────────────────────────────────────────
# PULL: PostgreSQL → SQLite
# ─────────────────────────────────────────────────────────────

def pull_from_postgres(since=None):
    """Тянем из PostgreSQL всё изменённое после since и применяем к SQLite."""
    count  = 0
    errors = []

    try:
        conn = _pg_connect()
    except Exception as e:
        return 0, [f'Нет соединения с PostgreSQL: {e}']

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        for model_path in SYNC_MODELS:
            app_label, model_name = model_path.split('.')
            try:
                model = get_model(app_label, model_name)
            except LookupError:
                continue

            table      = model._meta.db_table
            has_update = any(f.name == 'updated_at' for f in model._meta.get_fields())

            if has_update and since:
                cur.execute(f'SELECT * FROM {table} WHERE updated_at > %s', [since])
            else:
                cur.execute(f'SELECT * FROM {table}')

            rows = cur.fetchall()
            for row in rows:
                try:
                    _upsert_local(model, dict(row))
                    count += 1
                except Exception as e:
                    errors.append(f'{model_path}#{row.get("id")}: {e}')
    finally:
        conn.close()

    return count, errors


def _upsert_local(model, data: dict):
    """Обновляем или создаём запись в локальном SQLite."""
    pk = data.pop('id', None)
    if pk is None:
        return
    # Убираем поля, которых нет в модели
    field_names = {f.attname for f in model._meta.concrete_fields}
    clean = {k: v for k, v in data.items() if k in field_names}
    model.objects.update_or_create(pk=pk, defaults=clean)


# ─────────────────────────────────────────────────────────────
# Полная синхронизация
# ─────────────────────────────────────────────────────────────

def run_full_sync():
    """
    1. PUSH локальных изменений → PostgreSQL
    2. PULL изменений с PostgreSQL → SQLite
    3. Обновляем SyncState
    """
    state = SyncState.get()
    state.syncing = True
    state.save(update_fields=['syncing'])

    result = {'push_count': 0, 'pull_count': 0, 'errors': []}
    try:
        push_n, push_err = push_to_postgres()
        result['push_count'] = push_n
        result['errors'].extend(push_err)

        pull_n, pull_err = pull_from_postgres(since=state.last_sync)
        result['pull_count'] = pull_n
        result['errors'].extend(pull_err)

        state.last_sync = timezone.now()
        state.db_mode   = 'postgres'
    except Exception as e:
        result['errors'].append(str(e))
    finally:
        state.syncing = False
        state.save(update_fields=['syncing', 'last_sync', 'db_mode'])

    return result
