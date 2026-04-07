"""
Purchases views: supplier CRUD, purchase order create/confirm/cancel.
"""
import json
from decimal import Decimal
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse

from .models import Supplier, PurchaseOrder, PurchaseItem
from .forms import SupplierForm, PurchaseOrderForm
from catalog.models import Product, PriceHistory
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
                old_price = item.product.price_purchase
                item.product.stock_quantity += item.quantity
                item.product.price_purchase = item.price
                item.product.save(update_fields=['stock_quantity', 'price_purchase'])

                if old_price != item.price:
                    PriceHistory.objects.create(
                        product=item.product,
                        user=request.user,
                        price_purchase=item.price,
                        note=f'Закупка #{order.pk}'
                    )

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
def add_product_to_purchase(request, product_pk):
    """POST: add a product to a draft purchase order (or create a new draft)."""
    if request.method != 'POST':
        return redirect('product_detail', pk=product_pk)

    product = get_object_or_404(Product, pk=product_pk, user=request.user)
    purchase_pk = request.POST.get('purchase_pk')
    qty = max(1, int(request.POST.get('qty', 1)))
    price = Decimal(str(request.POST.get('price', product.price_purchase or '0')))

    if purchase_pk == 'new' or not purchase_pk:
        order = PurchaseOrder.objects.create(user=request.user, status='draft', total_price=Decimal('0'))
    else:
        order = get_object_or_404(PurchaseOrder, pk=purchase_pk, user=request.user, status='draft')

    item, created = PurchaseItem.objects.get_or_create(
        order=order, product=product,
        defaults={'quantity': qty, 'price': price}
    )
    if not created:
        item.quantity += qty
        item.save(update_fields=['quantity'])

    # Recalc order total
    order.total_price = sum(i.quantity * i.price for i in order.items.all())
    order.save(update_fields=['total_price'])

    messages.success(request, f'"{product.name}" добавлен в закупку #{order.pk}')
    return redirect('product_detail', pk=product_pk)


@login_required
def auto_purchase_create(request):
    """Create a draft purchase order from all low-stock products."""
    if request.method != 'POST':
        return redirect('purchase_list')

    low_stock = Product.objects.filter(
        user=request.user,
        is_active=True,
        min_stock__gt=0,
        stock_quantity__lte=models.F('min_stock')
    )

    if not low_stock.exists():
        messages.info(request, 'Нет товаров с низким остатком (остаток ≤ мин. остаток).')
        return redirect('purchase_list')

    order = PurchaseOrder.objects.create(user=request.user, status='draft', total_price=Decimal('0'))
    total = Decimal('0')
    count = 0
    for product in low_stock:
        need_qty = product.min_stock - product.stock_quantity + product.min_stock
        price = product.price_purchase or Decimal('0')
        PurchaseItem.objects.create(order=order, product=product, quantity=need_qty, price=price)
        total += need_qty * price
        count += 1

    order.total_price = total
    order.save(update_fields=['total_price'])

    messages.success(request, f'Создан авто-заказ #{order.pk} из {count} товаров с низким остатком.')
    return redirect('purchase_detail', pk=order.pk)


@login_required
def purchase_import(request, pk):
    """Upload Excel/CSV to fill a purchase order with items."""
    order = get_object_or_404(PurchaseOrder, pk=pk, user=request.user, status='draft')

    if request.method == 'POST' and request.FILES.get('file'):
        import pandas as pd
        import tempfile

        f = request.FILES['file']
        suffix = '.xlsx' if f.name.endswith(('.xlsx', '.xls')) else '.csv'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            for chunk in f.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            if suffix == '.csv':
                df = pd.read_csv(tmp_path, dtype=str)
            else:
                df = pd.read_excel(tmp_path, dtype=str)
        except Exception as e:
            messages.error(request, f'Ошибка чтения файла: {e}')
            return redirect('purchase_import', pk=pk)
        finally:
            try:
                import os
                os.unlink(tmp_path)
            except Exception:
                pass

        # Get column mapping from POST
        col_oem = request.POST.get('col_oem', '')
        col_name = request.POST.get('col_name', '')
        col_qty = request.POST.get('col_qty', '')
        col_price = request.POST.get('col_price', '')

        columns = list(df.columns)
        added = 0
        skipped = 0

        for _, row in df.iterrows():
            def cell(col):
                if col and col in row:
                    v = str(row[col]).strip()
                    return '' if v.lower() in ('nan', 'none', '') else v
                return ''

            oem = cell(col_oem)
            name = cell(col_name)
            try:
                qty = max(1, int(float(cell(col_qty) or '1')))
            except (ValueError, TypeError):
                qty = 1
            try:
                price = Decimal(cell(col_price).replace(',', '.') or '0')
            except Exception:
                price = Decimal('0')

            # Find product by OEM or name
            product = None
            if oem:
                product = Product.objects.filter(user=request.user, oem_number__iexact=oem).first()
            if not product and name:
                product = Product.objects.filter(user=request.user, name__iexact=name).first()

            if product:
                item, created = PurchaseItem.objects.get_or_create(
                    order=order, product=product,
                    defaults={'quantity': qty, 'price': price}
                )
                if not created:
                    item.quantity += qty
                    if price:
                        item.price = price
                    item.save()
                added += 1
            else:
                skipped += 1

        order.total_price = sum(i.quantity * i.price for i in order.items.all())
        order.save(update_fields=['total_price'])

        messages.success(request, f'Импорт завершён: добавлено {added}, пропущено (не найдено) {skipped}.')
        return redirect('purchase_detail', pk=pk)

    # GET — show upload form with column selection
    return render(request, 'purchases/purchase_import.html', {'order': order})


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
