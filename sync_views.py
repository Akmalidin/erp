"""
Sync views: API endpoints for offline ↔ server synchronization.
"""
import json
import threading
from django.http import JsonResponse, StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

# Global sync state (per-process, single user desktop app)
_sync_state = {
    'running': False,
    'steps': [],       # list of {msg, status: 'ok'|'error'|'pending'}
    'done': False,
    'error': None,
}
_sync_lock = threading.Lock()


def _reset_state():
    _sync_state.update({
        'running': True,
        'steps': [],
        'done': False,
        'error': None,
    })


def _add_step(msg, status='ok'):
    _sync_state['steps'].append({'msg': msg, 'status': status})


@login_required
@require_POST
def sync_run(request):
    """Run full sync: push offline data → pull server data. Returns SSE stream."""
    from django.db import connections

    if 'sqlite_cache' not in connections.databases:
        return JsonResponse({
            'ok': False,
            'error': 'Нет подключения к серверу. Синхронизация недоступна в офлайн-режиме.',
        })

    with _sync_lock:
        if _sync_state['running']:
            return JsonResponse({'ok': False, 'error': 'Синхронизация уже запущена'})
        _reset_state()

    def do_sync():
        try:
            import sync_manager
            from crm.models import Client
            from orders.models import Order, OrderItem, OrderPayment

            # ── Step 1: Count offline data ────────────────────────────────────
            pg_client_sync_ids = set(
                Client.objects.using('default').exclude(sync_id=None)
                .values_list('sync_id', flat=True)
            )
            pg_order_sync_ids = set(
                Order.objects.using('default').exclude(sync_id=None)
                .values_list('sync_id', flat=True)
            )

            offline_clients = list(
                Client.objects.using('sqlite_cache').exclude(sync_id=None)
                .exclude(sync_id__in=pg_client_sync_ids)
            )
            offline_orders = list(
                Order.objects.using('sqlite_cache').exclude(sync_id=None)
                .exclude(sync_id__in=pg_order_sync_ids)
            )

            total_offline = len(offline_clients) + len(offline_orders)
            if total_offline:
                _add_step(f'Найдено офлайн-записей: {len(offline_clients)} клиентов, {len(offline_orders)} заказов', 'ok')
            else:
                _add_step('Офлайн-изменений нет — база актуальна', 'ok')

            # ── Step 2: Push clients ──────────────────────────────────────────
            client_id_map = {}
            if offline_clients:
                pushed = 0
                errors = 0
                for c in offline_clients:
                    try:
                        pg_c = Client.objects.using('default').create(
                            user_id=c.user_id, name=c.name, phone=c.phone,
                            email=c.email, company_name=c.company_name,
                            address=c.address, notes=c.notes,
                            discount_percent=c.discount_percent,
                            debt=c.debt, portal_enabled=c.portal_enabled,
                            sync_id=c.sync_id,
                        )
                        client_id_map[c.pk] = pg_c.pk
                        pushed += 1
                    except Exception as e:
                        errors += 1
                msg = f'Клиенты → сервер: {pushed} загружено'
                if errors:
                    msg += f', {errors} ошибок'
                _add_step(msg, 'error' if errors and not pushed else 'ok')

            # ── Step 3: Push orders ───────────────────────────────────────────
            if offline_orders:
                pushed = 0
                errors = 0
                for o in offline_orders:
                    try:
                        pg_client_id = client_id_map.get(o.client_id, o.client_id)
                        items = list(OrderItem.objects.using('sqlite_cache').filter(order=o))
                        payments = list(OrderPayment.objects.using('sqlite_cache').filter(order=o))

                        pg_o = Order.objects.using('default').create(
                            user_id=o.user_id, client_id=pg_client_id,
                            total_price=o.total_price, paid_amount=o.paid_amount,
                            payment_method=o.payment_method, status=o.status,
                            notes=o.notes, discount_type=o.discount_type,
                            discount_value=o.discount_value,
                            is_debt_recorded=o.is_debt_recorded,
                            created_at=o.created_at, sync_id=o.sync_id,
                        )
                        for item in items:
                            OrderItem.objects.using('default').create(
                                order=pg_o, product_id=item.product_id,
                                quantity=item.quantity, price=item.price,
                                discount_percent=item.discount_percent,
                            )
                        for pay in payments:
                            OrderPayment.objects.using('default').create(
                                order=pg_o, amount=pay.amount, method=pay.method,
                                note=pay.note, created_at=pay.created_at,
                            )
                        pushed += 1
                    except Exception as e:
                        errors += 1

                items_count = sum(
                    OrderItem.objects.using('sqlite_cache').filter(order=o).count()
                    for o in offline_orders
                )
                msg = f'Заказы → сервер: {pushed} заказов ({items_count} позиций)'
                if errors:
                    msg += f', {errors} ошибок'
                _add_step(msg, 'error' if errors and not pushed else 'ok')

            # ── Step 4: Pull server data ──────────────────────────────────────
            _add_step('Загрузка данных с сервера...', 'ok')
            sync_manager.pull_server_data()

            # Count what was pulled
            pg_clients = Client.objects.using('default').count()
            pg_orders = Order.objects.using('default').count()
            _add_step(f'Получено с сервера: {pg_clients} клиентов, {pg_orders} заказов', 'ok')

            _sync_state['done'] = True
            _sync_state['running'] = False

        except Exception as e:
            _add_step(f'Критическая ошибка: {e}', 'error')
            _sync_state['error'] = str(e)
            _sync_state['done'] = True
            _sync_state['running'] = False

    thread = threading.Thread(target=do_sync, daemon=True)
    thread.start()

    return JsonResponse({'ok': True, 'started': True})


@login_required
def sync_status(request):
    """Poll sync progress."""
    return JsonResponse({
        'running': _sync_state['running'],
        'steps': _sync_state['steps'],
        'done': _sync_state['done'],
        'error': _sync_state['error'],
    })
