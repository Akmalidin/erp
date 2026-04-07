"""
Client portal views. Authentication via phone + password stored on crm.Client.
Session key: portal_client_id (int: client PK).
Cart key: portal_cart (dict: {product_id_str: qty}).
"""
from functools import wraps
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator

from crm.models import Client
from orders.models import Order, OrderItem
from catalog.models import Product, PriceLevel
from .models import OrderNote, PortalNotification


# ─────────────────────────────────────────────
# Auth decorator
# ─────────────────────────────────────────────

def portal_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        client_id = request.session.get('portal_client_id')
        if not client_id:
            return redirect('portal_login')
        try:
            request.portal_client = Client.objects.select_related('user').get(
                pk=client_id, portal_enabled=True
            )
        except Client.DoesNotExist:
            request.session.pop('portal_client_id', None)
            return redirect('portal_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def _notify_admin(client, text, url=''):
    """Create a portal notification for the client's admin."""
    PortalNotification.objects.create(
        user=client.user,
        client=client,
        text=text,
        url=url,
    )


# ─────────────────────────────────────────────
# Auth views
# ─────────────────────────────────────────────

def portal_login(request):
    if request.session.get('portal_client_id'):
        return redirect('portal_dashboard')

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')

        # Normalize phone
        digits = ''.join(c for c in phone if c.isdigit())

        client = None
        for c in Client.objects.filter(portal_enabled=True).iterator():
            c_digits = ''.join(ch for ch in c.phone if ch.isdigit())
            if c_digits and c_digits == digits:
                client = c
                break

        if client and client.portal_password and check_password(password, client.portal_password):
            request.session['portal_client_id'] = client.pk
            request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
            return redirect('portal_dashboard')
        else:
            messages.error(request, 'Неверный номер телефона или пароль')

    return render(request, 'portal/login.html')


def portal_logout(request):
    request.session.pop('portal_client_id', None)
    request.session.pop('portal_cart', None)
    return redirect('portal_login')


# ─────────────────────────────────────────────
# Dashboard — order list
# ─────────────────────────────────────────────

@portal_required
def portal_dashboard(request):
    client = request.portal_client
    orders = Order.objects.filter(
        client=client, user=client.user
    ).prefetch_related('items__product').order_by('-created_at')

    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'portal/dashboard.html', {
        'client': client,
        'page_obj': page_obj,
    })


# ─────────────────────────────────────────────
# Order detail + notes
# ─────────────────────────────────────────────

@portal_required
def portal_order_detail(request, pk):
    client = request.portal_client
    order = get_object_or_404(Order, pk=pk, client=client, user=client.user)
    items = order.items.select_related('product').all()
    notes = order.portal_notes.select_related('client').all()

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        item_id = request.POST.get('item_id', '')
        if text:
            item = None
            if item_id:
                try:
                    item = items.get(pk=int(item_id))
                except (OrderItem.DoesNotExist, ValueError):
                    pass
            OrderNote.objects.create(
                order=order,
                item=item,
                client=client,
                author_type='client',
                text=text,
            )
            # Notify admin
            item_label = f' к позиции «{item.product.name}»' if item and item.product else ''
            _notify_admin(
                client,
                f'{client.name} оставил заметку{item_label} к заказу #{order.pk}',
                url=reverse('order_detail', args=[order.pk]),
            )
            messages.success(request, 'Заметка добавлена')
            return redirect('portal_order_detail', pk=pk)

    return render(request, 'portal/order_detail.html', {
        'client': client,
        'order': order,
        'items': items,
        'notes': notes,
    })


# ─────────────────────────────────────────────
# Admin replies to a note
# ─────────────────────────────────────────────

def admin_reply_note(request, note_pk):
    """Admin adds a reply note to an order (author_type='admin')."""
    from django.contrib.auth.decorators import login_required
    if not request.user.is_authenticated:
        return redirect('login')

    note = get_object_or_404(OrderNote, pk=note_pk, order__user=request.user)
    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            OrderNote.objects.create(
                order=note.order,
                item=note.item,
                client=note.client,
                author_type='admin',
                text=text,
            )
    return redirect('order_detail', pk=note.order_id)


# ─────────────────────────────────────────────
# Product catalog (client view)
# ─────────────────────────────────────────────

@portal_required
def portal_catalog(request):
    client = request.portal_client
    admin_user = client.user

    products = Product.objects.filter(user=admin_user, is_active=True).select_related('category')

    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(
            name__icontains=query
        ) | Product.objects.filter(
            user=admin_user, is_active=True, oem_number__icontains=query
        )
        products = products.distinct()

    category_id = request.GET.get('category', '').strip()
    if category_id:
        try:
            products = products.filter(category_id=int(category_id))
        except (ValueError, TypeError):
            category_id = ''

    products = products.order_by('name')
    paginator = Paginator(products, 24)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Get default price level for pricing
    default_level = PriceLevel.get_default(admin_user)

    # Attach retail price
    products_list = []
    for p in page_obj:
        p.display_price = default_level.calculate_price(p.price_purchase) if default_level else p.price_purchase
        products_list.append(p)

    from catalog.models import Category
    categories = Category.objects.filter(user=admin_user)

    cart = request.session.get('portal_cart', {})

    return render(request, 'portal/catalog.html', {
        'client': client,
        'page_obj': page_obj,
        'products_list': products_list,
        'categories': categories,
        'query': query,
        'category_id': category_id,
        'cart_count': sum(cart.values()),
        'currency': admin_user.currency_symbol,
    })


# ─────────────────────────────────────────────
# Cart
# ─────────────────────────────────────────────

@portal_required
def portal_cart_add(request, product_id):
    client = request.portal_client
    admin_user = client.user

    product = get_object_or_404(Product, pk=product_id, user=admin_user, is_active=True)
    try:
        qty = max(1, int(request.POST.get('qty', 1)))
    except (ValueError, TypeError):
        qty = 1

    cart = request.session.get('portal_cart', {})
    key = str(product_id)
    cart[key] = cart.get(key, 0) + qty
    request.session['portal_cart'] = cart
    request.session.modified = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'total': sum(cart.values())})
    return redirect('portal_cart')


@portal_required
def portal_cart_remove(request, product_id):
    cart = request.session.get('portal_cart', {})
    cart.pop(str(product_id), None)
    request.session['portal_cart'] = cart
    request.session.modified = True
    return redirect('portal_cart')


@portal_required
def portal_cart_view(request):
    client = request.portal_client
    admin_user = client.user
    cart = request.session.get('portal_cart', {})
    default_level = PriceLevel.get_default(admin_user)

    items = []
    total = Decimal('0')
    for product_id_str, qty in list(cart.items()):
        try:
            product = Product.objects.get(pk=int(product_id_str), user=admin_user, is_active=True)
        except Product.DoesNotExist:
            continue
        price = default_level.calculate_price(product.price_purchase) if default_level else product.price_purchase
        subtotal = price * qty
        total += subtotal
        items.append({'product': product, 'qty': qty, 'price': price, 'subtotal': subtotal})

    return render(request, 'portal/cart.html', {
        'client': client,
        'items': items,
        'total': total,
        'currency': admin_user.currency_symbol,
    })


@portal_required
def portal_checkout(request):
    client = request.portal_client
    admin_user = client.user
    cart = request.session.get('portal_cart', {})

    if not cart:
        messages.error(request, 'Корзина пуста')
        return redirect('portal_cart')

    if request.method == 'POST':
        default_level = PriceLevel.get_default(admin_user)
        note_text = request.POST.get('note', '').strip()

        order = Order.objects.create(
            user=admin_user,
            client=client,
            status='new',
            discount_type='none',
            discount_value=Decimal('0'),
            total_price=Decimal('0'),
        )

        total = Decimal('0')
        for product_id_str, qty in cart.items():
            try:
                product = Product.objects.get(pk=int(product_id_str), user=admin_user, is_active=True)
            except Product.DoesNotExist:
                continue
            price = default_level.calculate_price(product.price_purchase) if default_level else product.price_purchase
            OrderItem.objects.create(order=order, product=product, quantity=qty, price=price)
            total += price * qty

        order.total_price = total
        order.save(update_fields=['total_price'])

        if note_text:
            OrderNote.objects.create(
                order=order,
                client=client,
                author_type='client',
                text=note_text,
            )

        # Clear cart
        request.session.pop('portal_cart', None)

        # Notify admin
        _notify_admin(
            client,
            f'{client.name} оформил новый заказ #{order.pk} на сумму {total:.0f} {admin_user.currency_symbol}',
            url=reverse('order_detail', args=[order.pk]),
        )

        messages.success(request, f'Заказ #{order.pk} оформлен! Менеджер свяжется с вами.')
        return redirect('portal_order_detail', pk=order.pk)

    return redirect('portal_cart')


# ─────────────────────────────────────────────
# Admin: notifications
# ─────────────────────────────────────────────

def admin_mark_notification_read(request, pk):
    """Mark a portal notification as read and redirect to its URL."""
    from django.contrib.auth.decorators import login_required
    if not request.user.is_authenticated:
        return redirect('login')
    notif = get_object_or_404(PortalNotification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    if notif.url:
        return redirect(notif.url)
    return redirect('portal_notifications')


def admin_notifications(request):
    """Admin page: list all portal notifications."""
    if not request.user.is_authenticated:
        return redirect('login')
    notifs = PortalNotification.objects.filter(user=request.user).select_related('client').order_by('-created_at')
    # Mark all as read on open
    notifs.filter(is_read=False).update(is_read=True)
    paginator = Paginator(notifs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'portal/admin_notifications.html', {'page_obj': page_obj})


# ─────────────────────────────────────────────
# Admin: manage client portal access
# ─────────────────────────────────────────────

def admin_portal_manage(request, client_pk):
    """Enable/disable portal access and set password for a client."""
    if not request.user.is_authenticated:
        return redirect('login')
    client = get_object_or_404(Client, pk=client_pk, user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'enable':
            new_password = request.POST.get('password', '').strip()
            if not new_password:
                messages.error(request, 'Введите пароль для клиента')
            elif len(new_password) < 4:
                messages.error(request, 'Пароль должен быть не менее 4 символов')
            else:
                client.portal_password = make_password(new_password)
                client.portal_enabled = True
                client.save(update_fields=['portal_password', 'portal_enabled'])
                messages.success(request, f'Доступ к порталу активирован. Пароль установлен.')
        elif action == 'change_password':
            new_password = request.POST.get('password', '').strip()
            if len(new_password) < 4:
                messages.error(request, 'Пароль должен быть не менее 4 символов')
            else:
                client.portal_password = make_password(new_password)
                client.save(update_fields=['portal_password'])
                messages.success(request, 'Пароль обновлён')
        elif action == 'disable':
            client.portal_enabled = False
            client.save(update_fields=['portal_enabled'])
            messages.success(request, 'Доступ к порталу отключён')

    return redirect('client_detail', pk=client_pk)
