"""
Sync manager: synchronize data between local SQLite and remote PostgreSQL.

Flow:
  push_offline_data() — find records in SQLite not yet in PostgreSQL (by sync_id), create them on server
  pull_server_data()  — copy all PostgreSQL records to SQLite for offline use
"""
import uuid
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SYNC_STATE_FILE = None  # Set from run_server.py after APP_DATA_DIR is known


def _state_file():
    import os
    path = Path(os.environ.get('APP_DATA_DIR', '.')) / 'sync_state.json'
    return path


def load_state():
    f = _state_file()
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def save_state(state):
    _state_file().write_text(json.dumps(state, default=str))


# ── PUSH: SQLite → PostgreSQL ─────────────────────────────────────────────────

def push_offline_data():
    """Push records created offline (in SQLite) to PostgreSQL."""
    from django.db import connections
    if 'sqlite_cache' not in connections.databases:
        return  # Not in online mode

    from crm.models import Client
    from orders.models import Order, OrderItem, OrderPayment

    pushed_clients = 0
    pushed_orders = 0

    # Get sync_ids already on the server (PostgreSQL = 'default')
    pg_client_sync_ids = set(
        Client.objects.using('default').exclude(sync_id=None).values_list('sync_id', flat=True)
    )
    pg_order_sync_ids = set(
        Order.objects.using('default').exclude(sync_id=None).values_list('sync_id', flat=True)
    )

    # New offline clients: have sync_id not in PostgreSQL
    offline_clients = Client.objects.using('sqlite_cache').exclude(sync_id=None).exclude(
        sync_id__in=pg_client_sync_ids
    )

    client_id_map = {}  # sqlite_id → pg_id

    for c in offline_clients:
        try:
            pg_c = Client.objects.using('default').create(
                user_id=c.user_id,
                name=c.name,
                phone=c.phone,
                email=c.email,
                company_name=c.company_name,
                address=c.address,
                notes=c.notes,
                discount_percent=c.discount_percent,
                debt=c.debt,
                portal_enabled=c.portal_enabled,
                sync_id=c.sync_id,
            )
            client_id_map[c.pk] = pg_c.pk
            pushed_clients += 1
        except Exception as e:
            logger.warning(f'Sync push client {c.pk}: {e}')

    # New offline orders: have sync_id not in PostgreSQL
    offline_orders = Order.objects.using('sqlite_cache').exclude(sync_id=None).exclude(
        sync_id__in=pg_order_sync_ids
    )

    for o in offline_orders:
        try:
            # Remap client_id if the client was also created offline
            pg_client_id = client_id_map.get(o.client_id, o.client_id)

            pg_o = Order.objects.using('default').create(
                user_id=o.user_id,
                client_id=pg_client_id,
                total_price=o.total_price,
                paid_amount=o.paid_amount,
                payment_method=o.payment_method,
                status=o.status,
                notes=o.notes,
                discount_type=o.discount_type,
                discount_value=o.discount_value,
                is_debt_recorded=o.is_debt_recorded,
                created_at=o.created_at,
                sync_id=o.sync_id,
            )

            # Push order items
            for item in OrderItem.objects.using('sqlite_cache').filter(order=o):
                OrderItem.objects.using('default').create(
                    order=pg_o,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=item.price,
                    discount_percent=item.discount_percent,
                )

            # Push payments
            for pay in OrderPayment.objects.using('sqlite_cache').filter(order=o):
                OrderPayment.objects.using('default').create(
                    order=pg_o,
                    amount=pay.amount,
                    method=pay.method,
                    note=pay.note,
                    created_at=pay.created_at,
                )

            pushed_orders += 1
        except Exception as e:
            logger.warning(f'Sync push order {o.pk}: {e}')

    logger.info(f'Sync push: {pushed_clients} clients, {pushed_orders} orders')
    return pushed_clients, pushed_orders


# ── PULL: PostgreSQL → SQLite ─────────────────────────────────────────────────

def pull_server_data():
    """Copy all PostgreSQL data to SQLite for offline use."""
    from django.db import connections
    if 'sqlite_cache' not in connections.databases:
        return

    from crm.models import Client
    from orders.models import Order, OrderItem, OrderPayment
    from catalog.models import Product

    # ── Products (read-only sync) ─────────────────────────────────────────────
    for p in Product.objects.using('default').all():
        try:
            Product.objects.using('sqlite_cache').update_or_create(
                pk=p.pk,
                defaults={
                    'user_id': p.user_id,
                    'name': p.name,
                    'oem_number': p.oem_number,
                    'price': p.price,
                    'price_purchase': p.price_purchase,
                    'stock_quantity': p.stock_quantity,
                    'is_active': p.is_active,
                    'category_id': p.category_id,
                    'barcode': p.barcode,
                    'description': p.description,
                    'unit': p.unit,
                    'location': p.location,
                }
            )
        except Exception:
            pass

    # ── Clients ───────────────────────────────────────────────────────────────
    for c in Client.objects.using('default').all():
        try:
            Client.objects.using('sqlite_cache').update_or_create(
                pk=c.pk,
                defaults={
                    'user_id': c.user_id,
                    'name': c.name,
                    'phone': c.phone,
                    'email': c.email,
                    'company_name': c.company_name,
                    'address': c.address,
                    'notes': c.notes,
                    'discount_percent': c.discount_percent,
                    'debt': c.debt,
                    'portal_enabled': c.portal_enabled,
                    'sync_id': c.sync_id,
                }
            )
        except Exception:
            pass

    # ── Orders ────────────────────────────────────────────────────────────────
    for o in Order.objects.using('default').select_related('client').all():
        try:
            Order.objects.using('sqlite_cache').update_or_create(
                pk=o.pk,
                defaults={
                    'user_id': o.user_id,
                    'client_id': o.client_id,
                    'total_price': o.total_price,
                    'paid_amount': o.paid_amount,
                    'payment_method': o.payment_method,
                    'status': o.status,
                    'notes': o.notes,
                    'discount_type': o.discount_type,
                    'discount_value': o.discount_value,
                    'is_debt_recorded': o.is_debt_recorded,
                    'created_at': o.created_at,
                    'sync_id': o.sync_id,
                }
            )
        except Exception:
            pass

    # ── Order Items ───────────────────────────────────────────────────────────
    for item in OrderItem.objects.using('default').all():
        try:
            OrderItem.objects.using('sqlite_cache').update_or_create(
                pk=item.pk,
                defaults={
                    'order_id': item.order_id,
                    'product_id': item.product_id,
                    'quantity': item.quantity,
                    'price': item.price,
                    'discount_percent': item.discount_percent,
                }
            )
        except Exception:
            pass

    # ── Order Payments ────────────────────────────────────────────────────────
    for pay in OrderPayment.objects.using('default').all():
        try:
            OrderPayment.objects.using('sqlite_cache').update_or_create(
                pk=pay.pk,
                defaults={
                    'order_id': pay.order_id,
                    'amount': pay.amount,
                    'method': pay.method,
                    'note': pay.note,
                    'created_at': pay.created_at,
                }
            )
        except Exception:
            pass

    logger.info('Sync pull complete')


# ── Assign sync_ids to records that don't have one ───────────────────────────

def assign_sync_ids_sqlite():
    """Set sync_id on existing SQLite records that lack one."""
    from crm.models import Client
    from orders.models import Order

    db = 'sqlite_cache' if 'sqlite_cache' in __import__('django.db', fromlist=['connections']).connections.databases else 'default'

    count = 0
    for c in Client.objects.using(db).filter(sync_id=None):
        c.sync_id = uuid.uuid4()
        c.save(using=db, update_fields=['sync_id'])
        count += 1
    for o in Order.objects.using(db).filter(sync_id=None):
        o.sync_id = uuid.uuid4()
        o.save(using=db, update_fields=['sync_id'])
        count += 1
    return count


def run_sync():
    """Full sync cycle: push offline data, then pull server data."""
    try:
        pushed = push_offline_data()
        pull_server_data()
        state = load_state()
        state['last_sync'] = __import__('datetime').datetime.now().isoformat()
        save_state(state)
        return pushed
    except Exception as e:
        logger.error(f'Sync error: {e}')
        return None
