"""
Sync views: delegates to desktop.sync.run_full_sync() for the heavy lifting.
Provides step-by-step progress via polling for the UI modal.
"""
import threading
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

_sync_state = {
    'running': False,
    'steps': [],
    'done': False,
    'error': None,
}
_sync_lock = threading.Lock()


def _reset():
    _sync_state.update({'running': True, 'steps': [], 'done': False, 'error': None})


def _step(msg, status='ok'):
    _sync_state['steps'].append({'msg': msg, 'status': status})


@login_required
@require_POST
def sync_run(request):
    """Start sync in background thread, return immediately."""
    with _sync_lock:
        if _sync_state['running']:
            return JsonResponse({'ok': False, 'error': 'Синхронизация уже запущена'})
        _reset()

    def _do():
        try:
            from desktop.sync import push_to_postgres, pull_from_postgres
            from desktop.models import SyncState, SyncLog

            # Count pending offline changes
            pending = SyncLog.objects.filter(synced=False).count()
            if pending:
                _step(f'Офлайн-изменений для загрузки: {pending} записей', 'ok')
            else:
                _step('Офлайн-изменений нет — всё актуально', 'ok')

            # PUSH: local → PostgreSQL
            _step('Отправка офлайн-данных на сервер...', 'ok')
            push_n, push_err = push_to_postgres()
            if push_err:
                for e in push_err[:3]:
                    _step(f'Ошибка: {e}', 'error')
            if push_n:
                _step(f'Загружено на сервер: {push_n} записей ✓', 'ok')
            else:
                _step('Новых офлайн-данных для отправки нет', 'ok')

            # PULL: PostgreSQL → local SQLite
            _step('Получение данных с сервера...', 'ok')
            state = SyncState.get()
            pull_n, pull_err = pull_from_postgres(since=state.last_sync)
            if pull_err:
                for e in pull_err[:3]:
                    _step(f'Ошибка: {e}', 'error')
            _step(f'Получено с сервера: {pull_n} записей ✓', 'ok')

            # Update sync state
            from django.utils import timezone
            state.last_sync = timezone.now()
            state.syncing = False
            state.save(update_fields=['last_sync', 'syncing'])

            _step('Синхронизация завершена успешно', 'ok')
            _sync_state['done'] = True
            _sync_state['running'] = False

        except Exception as e:
            _step(f'Критическая ошибка: {e}', 'error')
            _sync_state['error'] = str(e)
            _sync_state['done'] = True
            _sync_state['running'] = False

    threading.Thread(target=_do, daemon=True).start()
    return JsonResponse({'ok': True})


@login_required
def sync_status(request):
    """Poll current sync progress."""
    return JsonResponse({
        'running': _sync_state['running'],
        'steps': _sync_state['steps'],
        'done': _sync_state['done'],
        'error': _sync_state['error'],
    })
