"""
Order views: list, detail, create with items, status update.
"""
import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse

from .models import Order, OrderItem
from .forms import OrderForm
from catalog.models import Product, PriceLevel
from catalog.utils import get_smart_search_filter
from catalog.utils import get_smart_search_filter
from crm.models import Client, Shift
from warehouse.models import StockMovement, Warehouse


@login_required
def order_list(request):
    """List all orders with filters."""
    orders = Order.objects.select_related('client', 'user').filter(user=request.user)

    # Search
    query = request.GET.get('q', '').strip()
    if query:
        search_fields = ['client__name', 'pk', 'notes']
        orders = orders.filter(get_smart_search_filter(query, search_fields))

    status = request.GET.get('status')
    if status in ['new', 'processing', 'completed', 'cancelled']:
        orders = orders.filter(status=status)

    paginator = Paginator(orders, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status,
        'total_count': paginator.count,
    }
    return render(request, 'orders/list.html', context)


@login_required
def order_detail(request, pk):
    """Order detail with items."""
    order = get_object_or_404(Order.objects.select_related('client', 'user'), pk=pk, user=request.user)
    items = order.items.select_related('product').all()

    context = {
        'order': order,
        'items': items,
    }
    return render(request, 'orders/detail.html', context)


@login_required
def order_create(request):
    """Create a new order with items (AJAX + form)."""
    clients = Client.objects.filter(user=request.user).order_by('name')
    price_levels = PriceLevel.objects.filter(user=request.user)
    PriceLevel.create_defaults(request.user)

    if request.method == 'POST':
        client_id = request.POST.get('client')
        notes = request.POST.get('notes', '')
        paid_amount = request.POST.get('paid_amount', '0')
        items_json = request.POST.get('items_json', '[]')

        try:
            items_data = json.loads(items_json)
        except json.JSONDecodeError:
            messages.error(request, 'Ошибка данных позиций заказа')
            return redirect('order_create')

        if not items_data:
            messages.error(request, 'Добавьте хотя бы одну позицию')
            return redirect('order_create')

        is_quick_sale = request.POST.get('quick_sale') == '1'
        discount_type = request.POST.get('discount_type', 'none')
        discount_value = request.POST.get('discount_value', '0')

        # Create order
        client = None
        if is_quick_sale:
            client, _ = Client.objects.get_or_create(user=request.user, name='Розница')
        elif client_id:
            client = Client.objects.filter(pk=client_id, user=request.user).first()

        order = Order.objects.create(
            user=request.user,
            client=client,
            notes=notes,
            paid_amount=Decimal(paid_amount) if paid_amount else 0,
            status='completed' if is_quick_sale else 'new',
            discount_type=discount_type if discount_type in ('none', 'percent', 'fixed') else 'none',
            discount_value=Decimal(discount_value) if discount_value else 0,
        )

        subtotal = 0
        errors = []

        for item in items_data:
            try:
                product_id = int(item.get('product_id', 0))
                qty = int(item.get('quantity', 0))
                price = float(item.get('price', 0))
                item_discount = float(item.get('discount_percent', 0))

                if qty <= 0 or price <= 0:
                    continue

                product = Product.objects.get(pk=product_id, user=request.user)

                # Check stock
                if product.stock_quantity < qty:
                    errors.append(f'"{product.name}": недостаточно остатка (есть {product.stock_quantity})')
                    continue

                # Create order item
                oi = OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=qty,
                    price=price,
                    discount_percent=item_discount,
                )

                # Deduct stock
                product.stock_quantity -= qty
                product.save(update_fields=['stock_quantity'])

                # Record stock movement
                StockMovement.objects.create(
                    user=request.user,
                    product=product,
                    change=-qty,
                    movement_type='sale',
                    note=f'Заказ #{order.pk}'
                )

                subtotal += float(oi.total)

            except (Product.DoesNotExist, ValueError, TypeError):
                errors.append(f'Ошибка при добавлении позиции')

        # Apply order-level discount
        if order.discount_type == 'percent' and order.discount_value:
            total = subtotal * float(1 - order.discount_value / 100)
        elif order.discount_type == 'fixed' and order.discount_value:
            total = max(subtotal - float(order.discount_value), 0)
        else:
            total = subtotal

        order.total_price = total
        # Handle debt logic if completed immediately
        if order.status == 'completed' and order.client:
            due = order.total_price - order.paid_amount
            if due > 0 and not order.is_debt_recorded:
                order.client.debt += due
                order.client.save(update_fields=['debt'])
                order.is_debt_recorded = True

        order.save(update_fields=['total_price', 'is_debt_recorded'])

        if errors:
            for err in errors:
                messages.warning(request, err)

        if order.items.count() > 0:
            if is_quick_sale:
                messages.success(request, f'Заказ #{order.pk} завершен на сумму {total:,.2f} {request.user.currency_symbol}')
            else:
                messages.success(request, f'Заказ #{order.pk} создан на сумму {total:,.2f} {request.user.currency_symbol}')
            return redirect('order_detail', pk=order.pk)
        else:
            order.delete()
            messages.error(request, 'Не удалось создать заказ — позиции не добавлены')
            return redirect('order_create')

    import json as _json
    clients_data = {str(c.pk): float(c.discount_percent) for c in clients}
    context = {
        'clients': clients,
        'price_levels': price_levels,
        'clients_discount_json': _json.dumps(clients_data),
    }
    return render(request, 'orders/create.html', context)


@login_required
def order_edit(request, pk):
    """Edit an existing order."""
    order = get_object_or_404(Order.objects.select_related('client'), pk=pk, user=request.user)
    clients = Client.objects.filter(user=request.user).order_by('name')
    price_levels = PriceLevel.objects.filter(user=request.user)

    if request.method == 'POST':
        client_id = request.POST.get('client')
        notes = request.POST.get('notes', '')
        paid_amount = request.POST.get('paid_amount', '0')
        items_json = request.POST.get('items_json', '[]')

        try:
            items_data = json.loads(items_json)
        except json.JSONDecodeError:
            messages.error(request, 'Ошибка данных позиций')
            return redirect('order_edit', pk=order.pk)

        # 1. Reverse old stock and debt
        if order.is_debt_recorded and order.client:
            due = order.total_price - order.paid_amount
            order.client.debt -= due
            order.client.save(update_fields=['debt'])
            order.is_debt_recorded = False

        old_items = list(order.items.all())
        for item in old_items:
            if item.product:
                item.product.stock_quantity += item.quantity
                item.product.save(update_fields=['stock_quantity'])
                # StockMovement for return? Not necessarily if it's an edit, but good for audit
                StockMovement.objects.create(
                    user=request.user, product=item.product, change=item.quantity,
                    movement_type='manual', note=f'Корректировка заказа #{order.pk}'
                )

        # 2. Update order basic fields
        order.client = Client.objects.filter(pk=client_id, user=request.user).first() if client_id else None
        order.notes = notes
        order.paid_amount = Decimal(paid_amount) if paid_amount else 0
        order.items.all().delete()

        # 3. Create new items and deduct stock
        total = 0
        errors = []
        for item in items_data:
            try:
                p_id = int(item.get('product_id'))
                qty = int(item.get('quantity'))
                price = Decimal(str(item.get('price')))
                product = Product.objects.get(pk=p_id, user=request.user)

                if product.stock_quantity < qty:
                    errors.append(f'"{product.name}": недостаточно остатка')
                    # still proceed with what we have? No, better use old qty if editing?
                    # For simplicity, we just deduct what we can or error out.
                
                OrderItem.objects.create(order=order, product=product, quantity=qty, price=price)
                product.stock_quantity -= qty
                product.save(update_fields=['stock_quantity'])
                StockMovement.objects.create(
                    user=request.user, product=product, change=-qty,
                    movement_type='sale', note=f'Правка заказа #{order.pk}'
                )
                total += qty * price
            except:
                continue

        order.total_price = total
        
        # 4. Re-apply debt if completed
        if order.status == 'completed' and order.client:
            due = order.total_price - order.paid_amount
            if due > 0:
                order.client.debt += due
                order.client.save(update_fields=['debt'])
                order.is_debt_recorded = True
        
        order.save()
        if errors:
            for e in errors: messages.warning(request, e)
        messages.success(request, f'Заказ #{order.pk} обновлен')
        return redirect('order_detail', pk=order.pk)

    # For JS initialization
    items_data = []
    for item in order.items.select_related('product').all():
        items_data.append({
            'product_id': item.product.id if item.product else 0,
            'oem_number': item.product.oem_number if item.product else '',
            'name': item.product.name if item.product else 'Удаленный товар',
            'price': float(item.price),
            'price_purchase': float(item.product.price_purchase) if item.product else 0,
            'quantity': item.quantity,
            'max_stock': (item.product.stock_quantity + item.quantity) if item.product else item.quantity
        })

    context = {
        'order': order,
        'clients': clients,
        'price_levels': price_levels,
        'initial_items_json': json.dumps(items_data),
    }
    return render(request, 'orders/edit.html', context)


@login_required
def order_status_update(request, pk):
    """Update order status."""
    order = get_object_or_404(Order, pk=pk, user=request.user)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            old_status = order.get_status_display()
            order.status = new_status
            order.save(update_fields=['status', 'updated_at'])

            # Update debt if completed
            if new_status == 'completed' and order.client and not order.is_debt_recorded:
                due = order.total_price - order.paid_amount
                if due > 0:
                    order.client.debt += due
                    order.client.save(update_fields=['debt'])
                    order.is_debt_recorded = True
                    order.save(update_fields=['is_debt_recorded'])

            # If cancelled or returned, return stock and reverse debt if it was recorded
            if new_status in ['cancelled', 'returned']:
                if order.is_debt_recorded and order.client:
                    due = order.total_price - order.paid_amount
                    order.client.debt -= due
                    order.client.save(update_fields=['debt'])
                    order.is_debt_recorded = False
                    order.save(update_fields=['is_debt_recorded'])
                
                for item in order.items.select_related('product').all():
                    if item.product:
                        item.product.stock_quantity += item.quantity
                        item.product.save(update_fields=['stock_quantity'])
                        action_title = 'Отмена' if new_status == 'cancelled' else 'Возврат'
                        StockMovement.objects.create(
                            user=request.user,
                            product=item.product,
                            change=item.quantity,
                            movement_type='return',
                            note=f'{action_title} по заказу #{order.pk}'
                        )

            messages.success(request, f'Статус изменен: {old_status} → {order.get_status_display()}')

    return redirect('order_detail', pk=order.pk)


@login_required
def product_search_api(request):
    """API endpoint for searching products (used in order creation)."""
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        search_fields = ['oem_number', 'part_number', 'name', 'barcode']
        products = Product.objects.filter(
            get_smart_search_filter(query, search_fields),
            is_active=True,
            user=request.user,
        )[:20]

        levels = PriceLevel.objects.filter(user=request.user)

        results = [{
            'id': p.id,
            'oem_number': p.oem_number,
            'part_number': p.part_number,
            'name': p.name,
            'barcode': p.barcode,
            'price_purchase': str(p.price_purchase),
            'prices': {
                level.id: {
                    'name': level.name,
                    'price': str(level.calculate_price(p.price_purchase)),
                    'is_default': level.is_default,
                }
                for level in levels
            },
            'price_default': str(p.get_price()),
            'stock_quantity': p.stock_quantity,
            'location': p.location,
        } for p in products]

    return JsonResponse({'results': results})


@login_required
def quick_sale(request, product_id):
    """Instantly create a completed order for a single product."""
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=product_id, user=request.user)
        qty = int(request.POST.get('quantity', 1))

        if product.stock_quantity < qty:
            messages.error(request, f'Недостаточно товара (Остаток: {product.stock_quantity})')
            return redirect('product_list')

        client, _ = Client.objects.get_or_create(user=request.user, name='Розница')

        order = Order.objects.create(
            user=request.user,
            client=client,
            status='completed',
            notes='Быстрая продажа',
        )

        price = product.price_retail
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=qty,
            price=price
        )

        order.total_price = qty * price
        order.save(update_fields=['total_price'])

        product.stock_quantity -= qty
        product.save(update_fields=['stock_quantity'])

        StockMovement.objects.create(
            user=request.user,
            product=product,
            change=-qty,
            movement_type='sale',
            note=f'Быстрая продажа #{order.pk}'
        )

        messages.success(request, f'Быстрая продажа оформлена! Заказ #{order.pk}')
        return redirect('order_detail', pk=order.pk)
    
    return redirect('product_list')


@login_required
def print_receipt(request, pk):
    """Print 80mm thermal receipt."""
    order = get_object_or_404(Order.objects.select_related('client', 'user'), pk=pk, user=request.user)
    return render(request, 'orders/print_receipt.html', {'order': order})

@login_required
def print_invoice(request, pk):
    """Print A4 invoice/nakladnaya."""
    order = get_object_or_404(Order.objects.select_related('client', 'user'), pk=pk, user=request.user)
    items = order.items.select_related('product').all()
    return render(request, 'orders/print_invoice.html', {'order': order, 'items': items})


@login_required
def pos_view(request):
    """Point of Sale interface for fast cashier checkout."""
    # Check for open shift
    shift = Shift.objects.filter(user=request.user, is_open=True).first()
    if not shift:
        messages.warning(request, 'Смена не открыта. Сначала откройте кассовую смену.')
        return redirect('shift_open')

    clients = Client.objects.filter(user=request.user).order_by('name')
    default_warehouse = Warehouse.get_default(request.user)

    # Auto-close shift if it was opened on a previous day
    from django.utils import timezone as tz
    if shift and shift.opened_at.date() < tz.now().date():
        shift.closed_at = tz.now()
        shift.is_open = False
        shift.save(update_fields=['closed_at', 'is_open'])
        messages.warning(request, 'Смена автоматически закрыта (начался новый день). Откройте новую смену.')
        return redirect('shift_open')

    if request.method == 'POST':
        cart_json = request.POST.get('cart_json', '[]')
        client_id = request.POST.get('client_id')
        payment_method = request.POST.get('payment_method', 'cash')
        paid_cash = float(request.POST.get('paid_cash') or 0)
        paid_card = float(request.POST.get('paid_card') or 0)
        
        try:
            items_data = json.loads(cart_json)
        except json.JSONDecodeError:
            messages.error(request, 'Ошибка данных корзины')
            return redirect('pos_view')
            
        client = Client.objects.filter(pk=client_id, user=request.user).first() if client_id else None
        discount_type = request.POST.get('discount_type', 'none')
        discount_value = request.POST.get('discount_value', '0')

        try:
            total_paid = Decimal(str(paid_cash + paid_card))
        except:
            total_paid = Decimal('0.00')

        # Create order
        order = Order.objects.create(
            user=request.user,
            client=client,
            shift=shift,
            status='completed',
            paid_amount=total_paid,
            payment_method=payment_method,
            notes='POS продажа',
            discount_type=discount_type if discount_type in ('none', 'percent', 'fixed') else 'none',
            discount_value=Decimal(discount_value) if discount_value else Decimal('0'),
        )
        
        subtotal = Decimal('0.00')
        errors = []
        for item in items_data:
            try:
                product_id = int(item.get('id', 0))
                qty = int(item.get('qty', 0))
                price = Decimal(str(item.get('price', 0)))
                item_discount = Decimal(str(item.get('discount_percent', 0)))

                if qty <= 0 or price <= 0:
                    continue

                product = Product.objects.get(pk=product_id, user=request.user)

                if product.stock_quantity < qty:
                    errors.append(f'"{product.name}": недостаточно остатка (есть {product.stock_quantity})')

                oi = OrderItem.objects.create(order=order, product=product, quantity=qty, price=price, discount_percent=item_discount)

                product.stock_quantity -= qty
                product.save(update_fields=['stock_quantity'])

                StockMovement.objects.create(
                    user=request.user,
                    product=product,
                    warehouse=default_warehouse,
                    change=-qty,
                    movement_type='sale',
                    note=f'Касса (Sale #{order.pk})'
                )

                subtotal += oi.total
            except Exception as e:
                continue

        # Apply order-level discount
        if order.discount_type == 'percent' and order.discount_value:
            total = subtotal * (1 - order.discount_value / Decimal('100'))
        elif order.discount_type == 'fixed' and order.discount_value:
            total = max(subtotal - order.discount_value, Decimal('0'))
        else:
            total = subtotal

        order.total_price = total
        
        # Process Debt
        due = order.total_price - order.paid_amount
        if due > 0 and client:
            client.debt += due
            client.save(update_fields=['debt'])
            order.is_debt_recorded = True
            
        order.save(update_fields=['total_price', 'is_debt_recorded'])
        
        # Create CRM Payment records
        from crm.models import Payment
        if client:
            if paid_cash > 0:
                Payment.objects.create(user=request.user, client=client, amount=paid_cash, payment_type='cash', note=f'Чек #{order.pk}')
            if paid_card > 0:
                Payment.objects.create(user=request.user, client=client, amount=paid_card, payment_type='card', note=f'Чек #{order.pk}')
        
        if errors:
            for err in errors: messages.warning(request, err)

        return redirect('pos_sale_done', pk=order.pk)

    return render(request, 'orders/pos.html', {'clients': clients})


@login_required
def pos_sale_done(request, pk):
    """Post-sale screen: ask to print receipt or invoice."""
    order = get_object_or_404(Order.objects.select_related('client', 'user'), pk=pk, user=request.user)
    return render(request, 'orders/pos_sale_done.html', {'order': order})
