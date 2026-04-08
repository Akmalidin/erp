"""
Desktop API views.
/desktop/status/   — текущий режим + sync state (polling с фронтенда)
/desktop/sync/     — запустить синхронизацию (POST)
/desktop/pending-imports/ — список офлайн-импортов
"""
import os
import threading
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import SyncState, SyncLog, PendingImport


def _connectivity_from_file():
    """Читаем статус из файла, который пишет run_server.py."""
    app_data = os.environ.get('APP_DATA_DIR', '')
    if app_data:
        f = Path(app_data) / '.connectivity'
        if f.exists():
            return f.read_text().strip()
    # Если файла нет — смотрим на env (сервер стартовал в этом режиме)
    return os.environ.get('DB_MODE', 'sqlite')


@login_required
def desktop_status(request):
    """
    GET /desktop/status/
    Возвращает текущий режим БД и состояние синхронизации.
    Фронтенд опрашивает каждые 15 сек.
    """
    file_mode  = _connectivity_from_file()     # режим по факту (из файла мониторинга)
    active_mode = os.environ.get('DB_MODE', 'sqlite')  # режим, с которым запущен процесс

    state = SyncState.get()
    pending_count = SyncLog.objects.filter(synced=False).count()
    pending_imports = PendingImport.objects.filter(
        user=request.user, status=PendingImport.STATUS_PENDING
    ).count()

    return JsonResponse({
        'active_mode':      active_mode,      # с чем сейчас работаем
        'network_mode':     file_mode,        # что обнаружил монитор
        'switch_available': file_mode == 'postgres' and active_mode == 'sqlite',
        'syncing':          state.syncing,
        'last_sync':        state.last_sync.isoformat() if state.last_sync else None,
        'pending_changes':  pending_count,
        'pending_imports':  pending_imports,
    })


@csrf_exempt
@require_POST
@login_required
def desktop_sync(request):
    """
    POST /desktop/sync/
    Запускает синхронизацию в фоне, возвращает статус.
    """
    state = SyncState.get()
    if state.syncing:
        return JsonResponse({'ok': False, 'message': 'Синхронизация уже идёт'})

    def _do_sync():
        from .sync import run_full_sync
        result = run_full_sync()
        # После синхронизации запускаем офлайн-импорты
        _flush_pending_imports()
        return result

    threading.Thread(target=_do_sync, daemon=True).start()
    return JsonResponse({'ok': True, 'message': 'Синхронизация запущена'})


def _flush_pending_imports():
    """Пакетная загрузка офлайн-импортов после восстановления связи."""
    import json
    from catalog.models import Product, Category
    from django.contrib.auth import get_user_model
    User = get_user_model()

    pending = PendingImport.objects.filter(status=PendingImport.STATUS_PENDING)
    for imp in pending:
        imp.status = PendingImport.STATUS_SYNCING
        imp.save(update_fields=['status'])
        try:
            rows = json.loads(imp.rows_json)
            imp.rows_total = len(rows)
            done = 0
            for row in rows:
                _apply_import_row(row, imp.user)
                done += 1
            imp.rows_done  = done
            imp.status     = PendingImport.STATUS_DONE
        except Exception as e:
            imp.status    = PendingImport.STATUS_ERROR
            imp.error_msg = str(e)
        imp.save(update_fields=['status', 'error_msg', 'rows_total', 'rows_done'])


def _apply_import_row(row: dict, user):
    """Применяем одну строку из офлайн-импорта к БД."""
    from catalog.models import Product, Category
    oem  = str(row.get('oem_number', '')).strip()
    name = str(row.get('name', '')).strip()
    if not oem and not name:
        return

    cat_name = str(row.get('category', '')).strip()
    category = None
    if cat_name:
        category, _ = Category.objects.get_or_create(user=user, name=cat_name)

    defaults = {
        'name':           name or oem,
        'brand':          str(row.get('brand', '')).strip(),
        'is_active':      True,
    }
    if category:
        defaults['category'] = category
    try:
        defaults['price_purchase'] = float(row.get('price_purchase') or 0)
    except (ValueError, TypeError):
        pass

    if oem:
        Product.objects.update_or_create(
            user=user, oem_number=oem,
            defaults=defaults
        )
    else:
        Product.objects.update_or_create(
            user=user, name=name,
            defaults=defaults
        )


@login_required
def pending_imports(request):
    """GET /desktop/pending-imports/ — список офлайн-импортов."""
    items = PendingImport.objects.filter(user=request.user).values(
        'id', 'filename', 'status', 'rows_total', 'rows_done',
        'created_at', 'error_msg'
    )
    return JsonResponse({'imports': list(items)})
