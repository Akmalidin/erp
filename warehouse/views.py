"""
Warehouse views: stock overview and movement history.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator

from catalog.models import Product
from catalog.utils import get_smart_search_filter
from .models import StockMovement, Warehouse


@login_required
def warehouse_list(request):
    """Manage warehouse locations."""
    warehouses = Warehouse.objects.filter(user=request.user)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address', '')
        is_default = request.POST.get('is_default') == 'on'
        
        if is_default:
            Warehouse.objects.filter(user=request.user).update(is_default=False)
            
        Warehouse.objects.create(
            user=request.user,
            name=name,
            address=address,
            is_default=is_default
        )
        messages.success(request, f'Склад "{name}" добавлен')
        return redirect('warehouse_list')
        
    return render(request, 'warehouse/warehouses.html', {'warehouses': warehouses})


@login_required
def stock_transfer(request):
    """Transfer stock between warehouses."""
    warehouses = Warehouse.objects.filter(user=request.user)
    products = Product.objects.filter(user=request.user, is_active=True)
    
    if request.method == 'POST':
        product_id = request.POST.get('product')
        from_wh_id = request.POST.get('from_warehouse')
        to_wh_id = request.POST.get('to_warehouse')
        qty = int(request.POST.get('quantity', 0))
        
        if from_wh_id == to_wh_id:
            messages.error(request, 'Склады отправления и назначения должны быть разными')
        elif qty <= 0:
            messages.error(request, 'Количество должно быть больше нуля')
        else:
            product = get_object_or_404(Product, pk=product_id, user=request.user)
            from_wh = get_object_or_404(Warehouse, pk=from_wh_id, user=request.user)
            to_wh = get_object_or_404(Warehouse, pk=to_wh_id, user=request.user)
            
            # Record move from
            StockMovement.objects.create(
                user=request.user,
                product=product,
                warehouse=from_wh,
                change=-qty,
                movement_type='transfer',
                note=f'Перемещение на {to_wh.name}'
            )
            
            # Record move to
            StockMovement.objects.create(
                user=request.user,
                product=product,
                warehouse=to_wh,
                change=qty,
                movement_type='transfer',
                note=f'Перемещение со склада {from_wh.name}'
            )
            
            messages.success(request, f'Перемещено {qty} шт. "{product.name}"')
            return redirect('movement_history')
            
    return render(request, 'warehouse/transfer.html', {
        'warehouses': warehouses,
        'products': products
    })


@login_required
def stock_list(request):
    """Show current stock levels for all products."""
    products = Product.objects.select_related('category').filter(is_active=True, user=request.user)

    query = request.GET.get('q', '').strip()
    if query:
        search_fields = ['oem_number', 'name', 'part_number']
        products = products.filter(get_smart_search_filter(query, search_fields))

    stock_filter = request.GET.get('stock')
    if stock_filter == 'low':
        products = products.filter(stock_quantity__lte=5, stock_quantity__gt=0)
    elif stock_filter == 'out':
        products = products.filter(stock_quantity=0)
    elif stock_filter == 'in':
        products = products.filter(stock_quantity__gt=0)

    sort = request.GET.get('sort', 'stock_quantity')
    if sort in ['stock_quantity', '-stock_quantity', 'name', '-name', 'oem_number']:
        products = products.order_by(sort)

    paginator = Paginator(products, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'query': query,
        'stock_filter': stock_filter,
        'sort': sort,
        'total_count': paginator.count,
    }
    return render(request, 'warehouse/list.html', context)


@login_required
def movement_history(request):
    """Show all stock movements."""
    movements = StockMovement.objects.select_related('product').filter(user=request.user)

    query = request.GET.get('q', '').strip()
    if query:
        movements = movements.filter(
            Q(product__name__icontains=query) |
            Q(product__oem_number__icontains=query)
        )

    move_type = request.GET.get('type')
    if move_type in ['sale', 'import', 'manual', 'return']:
        movements = movements.filter(movement_type=move_type)

    paginator = Paginator(movements, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'query': query,
        'move_type': move_type,
        'total_count': paginator.count,
    }
    return render(request, 'warehouse/movements.html', context)


@login_required
def stock_adjust(request, pk):
    """Manually adjust stock for a product."""
    product = get_object_or_404(Product, pk=pk, user=request.user)
    default_warehouse = Warehouse.get_default(request.user)

    if request.method == 'POST':
        try:
            new_qty = int(request.POST.get('quantity', 0))
            note = request.POST.get('note', 'Ручная корректировка')
            change = new_qty - product.stock_quantity

            if change != 0:
                StockMovement.objects.create(
                    user=request.user,
                    product=product,
                    warehouse=default_warehouse,
                    change=change,
                    movement_type='manual',
                    note=note,
                )
                product.stock_quantity = new_qty
                product.save()
                messages.success(request, f'Остаток "{product.name}" обновлен: {new_qty} шт.')
            else:
                messages.info(request, 'Остаток не изменился')
        except (ValueError, TypeError):
            messages.error(request, 'Некорректное количество')

    return redirect('stock_list')


@login_required
def stock_bulk_add(request):
    """Bulk add quantity to all currently filtered products."""
    products = Product.objects.filter(is_active=True, user=request.user)
    default_warehouse = Warehouse.get_default(request.user)

    # Re-apply filters from the list view (mirroring stock_list logic)
    query = request.GET.get('q', '').strip()
    if query:
        search_fields = ['oem_number', 'part_number', 'name']
        products = products.filter(get_smart_search_filter(query, search_fields))

    stock_filter = request.GET.get('stock')
    if stock_filter == 'low':
        products = products.filter(stock_quantity__lte=5, stock_quantity__gt=0)
    elif stock_filter == 'out':
        products = products.filter(stock_quantity=0)
    elif stock_filter == 'in':
        products = products.filter(stock_quantity__gt=0)

    if request.method == 'POST':
        try:
            add_qty = int(request.POST.get('quantity', 0))
            note = request.POST.get('note', 'Массовое пополнение')
            
            if add_qty > 0:
                count = 0
                for product in products:
                    product.stock_quantity += add_qty
                    product.save(update_fields=['stock_quantity'])
                    
                    StockMovement.objects.create(
                        user=request.user,
                        product=product,
                        warehouse=default_warehouse,
                        change=add_qty,
                        movement_type='manual',
                        note=note,
                    )
                    count += 1
                
                messages.success(request, f'Остатки обновлены для {count} товаров: +{add_qty} шт.')
            else:
                messages.info(request, 'Количество должно быть больше нуля')
        except (ValueError, TypeError):
            messages.error(request, 'Некорректное количество')

    return redirect(request.META.get('HTTP_REFERER', 'stock_list'))


@login_required
def inventory_view(request):
    """View to perform bulk inventory recount."""
    products = Product.objects.filter(user=request.user, is_active=True).select_related('category')
    
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('prod_'):
                try:
                    product_id = int(key.replace('prod_', ''))
                    actual_qty = int(value)
                    product = products.filter(pk=product_id).first()
                    
                    if product and product.stock_quantity != actual_qty:
                        change = actual_qty - product.stock_quantity
                        StockMovement.objects.create(
                            user=request.user,
                            product=product,
                            change=change,
                            movement_type='manual',
                            note='Инвентаризация'
                        )
                        product.stock_quantity = actual_qty
                        product.save(update_fields=['stock_quantity'])
                except (ValueError, TypeError):
                    continue
        
        messages.success(request, 'Результаты инвентаризации применены')
        return redirect('inventory_list')

    context = {
        'products': products,
    }
    return render(request, 'warehouse/inventory.html', context)
