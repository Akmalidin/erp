"""
Purchases views: supplier CRUD, purchase order create/confirm/cancel.
"""
import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse

from .models import Supplier, PurchaseOrder, PurchaseItem
from .forms import SupplierForm, PurchaseOrderForm
from catalog.models import Product
from warehouse.models import StockMovement


# ═══════════════════════════════════════════
# SUPPLIERS
# ═══════════════════════════════════════════

@login_required
def supplier_list(request):
    """List suppliers; quick-create from the same page."""
    suppliers = Supplier.objects.filter(user=request.user)

    query = request.GET.get('q', '').strip()
    if query:
        suppliers = suppliers.filter(name__icontains=query) | \
                    Supplier.objects.filter(user=request.user, phone__icontains=query)
        suppliers = suppliers.distinct()

    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.user = request.user
            supplier.save()
            messages.success(request, f'Поставщик "{supplier.name}" добавлен')
            return redirect('supplier_list')
    else:
        form = SupplierForm()

    return render(request, 'purchases/supplier_list.html', {
        'suppliers': suppliers,
        'form': form,
        'query': query,
    })


@login_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk, user=request.user)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f'Поставщик "{supplier.name}" обновлен')
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'purchases/supplier_form.html', {'form': form, 'supplier': supplier})


@login_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk, user=request.user)
    if request.method == 'POST':
        name = supplier.name
        supplier.delete()
        messages.success(request, f'Поставщик "{name}" удален')
    return redirect('supplier_list')


# ═══════════════════════════════════════════
# PURCHASE ORDERS
# ═══════════════════════════════════════════

@login_required
def purchase_list(request):
    """List all purchase orders with filters."""
    purchases = PurchaseOrder.objects.filter(user=request.user).select_related('supplier')

    status = request.GET.get('status')
    if status:
        purchases = purchases.filter(status=status)

    supplier_id = request.GET.get('supplier')
    if supplier_id:
        purchases = purchases.filter(supplier_id=supplier_id)

    paginator = Paginator(purchases, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'purchases/purchase_list.html', {
        'page_obj': page_obj,
        'suppliers': Supplier.objects.filter(user=request.user),
        'status_filter': status,
        'supplier_id': supplier_id,
        'total_count': paginator.count,
    })


@login_required
def purchase_create(request):
    """Create a new purchase order draft with line items."""
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, user=request.user)
        items_json = request.POST.get('items_json', '[]')

        try:
            items_data = json.loads(items_json)
        except json.JSONDecodeError:
            messages.error(request, 'Ошибка данных позиций')
            return redirect('purchase_create')

        if not items_data:
            messages.error(request, 'Добавьте хотя бы одну позицию')
            form = PurchaseOrderForm(request.POST, user=request.user)
            return render(request, 'purchases/purchase_create.html', {
                'form': form,
                'suppliers': Supplier.objects.filter(user=request.user),
            })

        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()

            total = Decimal('0.00')
            for item in items_data:
                try:
                    product_id = int(item.get('product_id', 0))
                    qty = int(item.get('quantity', 0))
                    price = Decimal(str(item.get('price', 0)))
                    if qty <= 0:
                        continue
                    product = Product.objects.get(pk=product_id, user=request.user)
                    PurchaseItem.objects.create(order=order, product=product, quantity=qty, price=price)
                    total += qty * price
                except (Product.DoesNotExist, ValueError, TypeError):
                    continue

            order.total_price = total
            order.save(update_fields=['total_price'])

            messages.success(
                request,
                f'Закупка #{order.pk} создана как черновик. '
                f'Нажмите «Провести», чтобы обновить остатки.'
            )
            return redirect('purchase_detail', pk=order.pk)
    else:
        form = PurchaseOrderForm(user=request.user)

    return render(request, 'purchases/purchase_create.html', {
        'form': form,
        'suppliers': Supplier.objects.filter(user=request.user),
    })


@login_required
def purchase_detail(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk, user=request.user)
    items = order.items.select_related('product').all()
    return render(request, 'purchases/purchase_detail.html', {
        'order': order,
        'items': items,
    })


@login_required
def purchase_confirm(request, pk):
    """Confirm purchase: increment stock quantities, update purchase prices, record supplier debt."""
    order = get_object_or_404(PurchaseOrder, pk=pk, user=request.user)

    if order.status != 'draft':
        messages.error(request, 'Можно провести только черновик')
        return redirect('purchase_detail', pk=pk)

    if request.method == 'POST':
        for item in order.items.select_related('product').all():
            if item.product:
                item.product.stock_quantity += item.quantity
                item.product.price_purchase = item.price
                item.product.save(update_fields=['stock_quantity', 'price_purchase'])

                StockMovement.objects.create(
                    user=request.user,
                    product=item.product,
                    change=item.quantity,
                    movement_type='import',
                    note=f'Закупка #{order.pk}'
                )

        due = order.total_price - order.paid_amount
        if due > 0 and order.supplier:
            order.supplier.debt += due
            order.supplier.save(update_fields=['debt'])

        order.status = 'confirmed'
        order.save(update_fields=['status'])

        messages.success(request, f'Закупка #{order.pk} проведена! Остатки и закупочные цены обновлены.')
        return redirect('purchase_detail', pk=pk)

    return redirect('purchase_detail', pk=pk)


@login_required
def purchase_cancel(request, pk):
    """Cancel a purchase order, reversing stock if it was confirmed."""
    order = get_object_or_404(PurchaseOrder, pk=pk, user=request.user)

    if request.method == 'POST':
        if order.status == 'confirmed':
            for item in order.items.select_related('product').all():
                if item.product:
                    item.product.stock_quantity -= item.quantity
                    item.product.save(update_fields=['stock_quantity'])
                    StockMovement.objects.create(
                        user=request.user,
                        product=item.product,
                        change=-item.quantity,
                        movement_type='manual',
                        note=f'Отмена закупки #{order.pk}'
                    )

            due = order.total_price - order.paid_amount
            if due > 0 and order.supplier:
                order.supplier.debt -= due
                order.supplier.save(update_fields=['debt'])

        order.status = 'cancelled'
        order.save(update_fields=['status'])
        messages.success(request, f'Закупка #{order.pk} отменена')

    return redirect('purchase_detail', pk=pk)


@login_required
def product_search_api(request):
    """AJAX: search products for purchase order form."""
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        products = Product.objects.filter(
            user=request.user,
            is_active=True,
        ).filter(
            name__icontains=query
        ) | Product.objects.filter(
            user=request.user,
            is_active=True,
            oem_number__icontains=query
        )
        products = products.distinct()[:20]
        results = [{
            'id': p.id,
            'oem_number': p.oem_number,
            'name': p.name,
            'price_purchase': str(p.price_purchase),
            'stock_quantity': p.stock_quantity,
        } for p in products]

    return JsonResponse({'results': results})
