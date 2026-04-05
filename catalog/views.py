"""
Catalog views: product CRUD, import, categories, price levels.
"""
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone

from .models import Product, Category, PriceLevel, CarMake, CarModel
from .forms import ProductForm, CategoryForm, ImportForm, PriceLevelForm
from .utils import get_smart_search_filter
from warehouse.models import StockMovement


@login_required
def product_list(request):
    """Product catalog with search and filters."""
    # Ensure default price levels exist
    PriceLevel.create_defaults(request.user)

    products = Product.objects.select_related('category').filter(user=request.user)

    # Search
    query = request.GET.get('q', '').strip()
    if query:
        search_fields = [
            'oem_number', 'part_number', 'name', 'brand', 'barcode',
            'compatible_models__name', 'compatible_models__make__name'
        ]
        products = products.filter(get_smart_search_filter(query, search_fields)).distinct()

    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    # Stock filter
    stock_filter = request.GET.get('stock')
    if stock_filter == 'low':
        products = products.filter(stock_quantity__lte=5)
    elif stock_filter == 'out':
        products = products.filter(stock_quantity=0)
    elif stock_filter == 'in':
        products = products.filter(stock_quantity__gt=0)

    # Active filter
    active_filter = request.GET.get('active')
    if active_filter == '1':
        products = products.filter(is_active=True)
    elif active_filter == '0':
        products = products.filter(is_active=False)

    # Sorting
    sort = request.GET.get('sort', '-created_at')
    if sort in ['name', '-name', 'price_purchase', '-price_purchase', 'stock_quantity', '-stock_quantity', 'oem_number', '-oem_number', 'created_at', '-created_at']:
        products = products.order_by(sort)

    # Pagination
    paginator = Paginator(products, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.filter(user=request.user)
    default_level = PriceLevel.get_default(request.user)

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'query': query,
        'category_id': category_id,
        'stock_filter': stock_filter,
        'sort': sort,
        'total_count': paginator.count,
        'default_level': default_level,
    }
    return render(request, 'catalog/list.html', context)


@login_required
def product_detail(request, pk):
    """Product detail view with all price levels."""
    product = get_object_or_404(Product, pk=pk, user=request.user)
    movements = StockMovement.objects.filter(product=product, user=request.user).order_by('-created_at')[:20]
    all_prices = product.get_all_prices()
    context = {
        'product': product,
        'movements': movements,
        'all_prices': all_prices,
    }
    return render(request, 'catalog/detail.html', context)


@login_required
def print_price_list(request):
    """View to generate a printable price list with category selection."""
    selected_categories = request.GET.getlist('categories')
    include_no_category = request.GET.get('no_category') == '1'
    
    # If no selection made yet, show selection page
    if not selected_categories and not include_no_category and 'all' not in request.GET:
        categories = Category.objects.filter(user=request.user).annotate(product_count=models.Count('products'))
        no_cat_count = Product.objects.filter(user=request.user, category__isnull=True).count()
        return render(request, 'catalog/print_select.html', {
            'categories': categories,
            'no_cat_count': no_cat_count,
        })

    # Fetch selected categories
    products_qs = Product.objects.filter(user=request.user, is_active=True)
    
    if 'all' in request.GET:
        categories = Category.objects.filter(user=request.user).prefetch_related(
            models.Prefetch('products', queryset=products_qs)
        )
        uncategorized = products_qs.filter(category__isnull=True)
    else:
        categories = Category.objects.filter(user=request.user, id__in=selected_categories).prefetch_related(
            models.Prefetch('products', queryset=products_qs)
        )
        uncategorized = products_qs.filter(category__isnull=True) if include_no_category else []

    context = {
        'categories': categories,
        'uncategorized': uncategorized,
        'date': timezone.now(),
    }
    return render(request, 'catalog/print_price.html', context)


@login_required
def product_create(request):
    """Create new product."""
    if request.method == 'POST':
        form = ProductForm(request.POST, user=request.user)
        if form.is_valid():
            product = form.save(commit=False)
            product.user = request.user
            product.save()
            form.save_m2m()
            if product.stock_quantity > 0:
                StockMovement.objects.create(
                    user=request.user,
                    product=product,
                    change=product.stock_quantity,
                    movement_type='manual',
                    note='Начальный остаток'
                )
            messages.success(request, f'Товар "{product.name}" создан')
            return redirect('product_list')
    else:
        form = ProductForm(user=request.user)

    return render(request, 'catalog/form.html', {'form': form, 'title': 'Новый товар'})


@login_required
def product_edit(request, pk):
    """Edit existing product."""
    product = get_object_or_404(Product, pk=pk, user=request.user)

    if request.method == 'POST':
        old_qty = product.stock_quantity
        form = ProductForm(request.POST, instance=product, user=request.user)
        if form.is_valid():
            product = form.save()
            new_qty = product.stock_quantity
            if new_qty != old_qty:
                StockMovement.objects.create(
                    user=request.user,
                    product=product,
                    change=new_qty - old_qty,
                    movement_type='manual',
                    note='Ручная корректировка'
                )
            messages.success(request, f'Товар "{product.name}" обновлен')
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product, user=request.user)

    return render(request, 'catalog/form.html', {'form': form, 'title': 'Редактировать товар', 'product': product})


@login_required
def product_delete(request, pk):
    """Delete a product."""
    product = get_object_or_404(Product, pk=pk, user=request.user)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Товар "{name}" удален')
        return redirect('product_list')
    return render(request, 'catalog/confirm_delete.html', {'product': product})


def parse_number(value):
    """Parse a number from string, handling spaces and commas in prices like '1 200.00'."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    s = s.replace('\u00a0', '').replace(' ', '').replace(',', '.')
    for ch in ['₸', '₽', '$', '€', 'сом', 'тг', 'руб']:
        s = s.replace(ch, '')
    s = s.strip()
    if not s:
        return 0
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0


@login_required
def product_import(request):
    """Step 1: Upload file for import."""
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            file_name = file.name.lower()

            try:
                # Read file with pandas
                if file_name.endswith('.csv'):
                    try:
                        df = pd.read_csv(file, encoding='utf-8')
                    except UnicodeDecodeError:
                        file.seek(0)
                        df = pd.read_csv(file, encoding='cp1251')
                elif file_name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file)
                else:
                    messages.error(request, 'Неподдерживаемый формат файла')
                    return redirect('product_import')

                df = df.dropna(how='all')

                if len(df) == 0:
                    messages.error(request, 'Файл пуст')
                    return redirect('product_import')

                # Save file temporarily
                import tempfile, os
                tmp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tmp_imports')
                os.makedirs(tmp_dir, exist_ok=True)
                tmp_path = os.path.join(tmp_dir, f'import_{request.user.pk}_{int(timezone.now().timestamp())}.pkl')
                df.to_pickle(tmp_path)

                # Store in session
                request.session['import_tmp_file'] = tmp_path
                request.session['import_original_name'] = file.name

                return redirect('product_import_mapping')

            except Exception as e:
                messages.error(request, f'Ошибка чтения файла: {str(e)}')
                return redirect('product_import')
    else:
        form = ImportForm()

    return render(request, 'catalog/import.html', {'form': form})


@login_required
def product_import_mapping(request):
    """Step 2: User maps file columns to product fields."""
    import os

    tmp_path = request.session.get('import_tmp_file')
    original_name = request.session.get('import_original_name', 'файл')

    if not tmp_path or not os.path.exists(tmp_path):
        messages.error(request, 'Файл не найден. Загрузите заново.')
        return redirect('product_import')

    try:
        df = pd.read_pickle(tmp_path)
    except Exception:
        messages.error(request, 'Ошибка чтения файла. Загрузите заново.')
        return redirect('product_import')

    # Get column names (original, not normalized)
    columns = [str(col).strip() for col in df.columns.tolist()]
    total_rows = len(df)

    # Preview first 5 rows
    preview_rows = []
    for idx, row in df.head(5).iterrows():
        preview_rows.append([str(val) if not pd.isna(val) else '' for val in row.values])

    # Fields that user can map to
    fields = [
        {'key': 'name', 'label': 'Название *', 'required': True,
         'description': 'Наименование товара (обязательно)'},
        {'key': 'oem_number', 'label': 'OEM номер', 'required': False,
         'description': 'Оригинальный номер детали'},
        {'key': 'part_number', 'label': 'Артикул / Заводской №', 'required': False,
         'description': 'Артикул или заводской номер'},
        {'key': 'price_purchase', 'label': 'Закупочная цена', 'required': False,
         'description': 'Цена из прайс-листа'},
        {'key': 'stock_quantity', 'label': 'Остаток на складе', 'required': False,
         'description': 'Количество товара'},
        {'key': 'brand', 'label': 'Бренд / Производитель', 'required': False,
         'description': 'Бренд или производитель'},
        {'key': 'category', 'label': 'Категория', 'required': False,
         'description': 'Группа / категория товара'},
    ]

    # Try auto-suggest mapping
    auto_map = {}
    column_map_hints = {
        'name': ['название', 'name', 'наименование', 'товар', 'описание', 'деталь'],
        'oem_number': ['oem', 'оем', 'oem №', 'oem номер'],
        'part_number': ['артикул', 'заводской', 'part_number', 'part number', 'каталожный', 'номер'],
        'price_purchase': ['цена', 'price', 'стоимость', 'сом', 'закупочная', 'розничная'],
        'stock_quantity': ['остаток', 'stock', 'количество', 'кол', 'qty', 'наличие'],
        'brand': ['бренд', 'brand', 'производитель', 'марка', 'фирма'],
        'category': ['категория', 'category', 'группа', 'тип', 'раздел'],
    }

    for field_key, hints in column_map_hints.items():
        for idx, col in enumerate(columns):
            col_lower = col.lower()
            for hint in hints:
                if hint in col_lower or col_lower in hint:
                    if idx not in auto_map.values():
                        auto_map[field_key] = idx
                        break
            if field_key in auto_map:
                break

    context = {
        'columns': columns,
        'total_rows': total_rows,
        'preview_rows': preview_rows,
        'fields': fields,
        'auto_map': auto_map,
        'original_name': original_name,
    }
    return render(request, 'catalog/import_mapping.html', context)


@login_required
def product_import_process(request):
    """Step 3: Process the import with user-defined column mapping."""
    import os

    if request.method != 'POST':
        return redirect('product_import')

    tmp_path = request.session.get('import_tmp_file')
    if not tmp_path or not os.path.exists(tmp_path):
        messages.error(request, 'Файл не найден. Загрузите заново.')
        return redirect('product_import')

    try:
        df = pd.read_pickle(tmp_path)
    except Exception:
        messages.error(request, 'Ошибка чтения файла.')
        return redirect('product_import')

    columns = [str(col).strip() for col in df.columns.tolist()]

    # Read user's column mapping from POST
    field_keys = ['name', 'oem_number', 'part_number', 'price_purchase',
                  'stock_quantity', 'brand', 'category']

    user_mapping = {}  # field_key -> column_index
    for fk in field_keys:
        val = request.POST.get(f'map_{fk}', '')
        if val != '' and val != '-1':
            try:
                col_idx = int(val)
                if 0 <= col_idx < len(columns):
                    user_mapping[fk] = col_idx
            except (ValueError, TypeError):
                pass

    # Check required
    if 'name' not in user_mapping:
        messages.error(request, 'Не указан столбец "Название". Это обязательное поле.')
        return redirect('product_import_mapping')

    # Process rows
    created = 0
    updated = 0
    errors = 0

    for idx, row in df.iterrows():
        try:
            def get_val(field_key, default=''):
                if field_key not in user_mapping:
                    return default
                val = row.iloc[user_mapping[field_key]]
                if pd.isna(val):
                    return default
                return val

            name = str(get_val('name', '')).strip()
            if not name or name.lower() == 'nan':
                errors += 1
                continue

            oem = str(get_val('oem_number', '')).strip()
            if oem.lower() == 'nan':
                oem = ''

            part_number = str(get_val('part_number', '')).strip()
            if part_number.lower() == 'nan':
                part_number = ''

            price_purchase = parse_number(get_val('price_purchase', 0))
            stock_qty = int(parse_number(get_val('stock_quantity', 0)))

            brand = str(get_val('brand', '')).strip()
            if brand.lower() == 'nan':
                brand = ''

            category_obj = None
            cat_name = str(get_val('category', '')).strip()
            if cat_name and cat_name.lower() != 'nan':
                category_obj, _ = Category.objects.get_or_create(user=request.user, name=cat_name)

            # Update or create by OEM
            if oem:
                product, is_created = Product.objects.update_or_create(
                    oem_number=oem,
                    user=request.user,
                    defaults={
                        'name': name,
                        'part_number': part_number,
                        'brand': brand,
                        'price_purchase': price_purchase,
                        'stock_quantity': stock_qty,
                        'category': category_obj,
                    }
                )
            else:
                product = Product.objects.create(
                    user=request.user,
                    oem_number='',
                    name=name,
                    part_number=part_number,
                    brand=brand,
                    price_purchase=price_purchase,
                    stock_quantity=stock_qty,
                    category=category_obj,
                )
                is_created = True

            if is_created:
                created += 1
            else:
                updated += 1

        except Exception:
            errors += 1
            continue

    # Cleanup temp file
    try:
        os.remove(tmp_path)
    except OSError:
        pass
    request.session.pop('import_tmp_file', None)
    request.session.pop('import_original_name', None)

    messages.success(
        request,
        f'Импорт завершен: создано {created}, обновлено {updated}, ошибок {errors}'
    )
    return redirect('product_list')


@login_required
def product_bulk_edit(request):
    """View to edit multiple products at once."""
    products_qs = Product.objects.filter(user=request.user).select_related('category').order_by('name')
    
    # Filter by category if provided
    category_id = request.GET.get('category')
    if category_id:
        products_qs = products_qs.filter(category_id=category_id)

    # Search
    query = request.GET.get('q', '').strip()
    if query:
        search_fields = [
            'oem_number', 'part_number', 'name', 'barcode',
            'compatible_models__name', 'compatible_models__make__name'
        ]
        products_qs = products_qs.filter(get_smart_search_filter(query, search_fields))

    if request.method == 'POST':
        updated_count = 0
        for key, value in request.POST.items():
            if key.startswith('name_'):
                try:
                    product_id = int(key.replace('name_', ''))
                    product = Product.objects.filter(pk=product_id, user=request.user).first()
                    if product:
                        # Get other fields
                        new_name = value.strip()
                        new_oem = request.POST.get(f'oem_{product_id}', '').strip()
                        new_price = parse_number(request.POST.get(f'price_{product_id}', '0'))
                        new_stock = int(parse_number(request.POST.get(f'stock_{product_id}', '0')))
                        
                        changed = False
                        if product.name != new_name: product.name = new_name; changed = True
                        if product.oem_number != new_oem: product.oem_number = new_oem; changed = True
                        if float(product.price_purchase) != float(new_price): product.price_purchase = new_price; changed = True
                        
                        if product.stock_quantity != new_stock:
                            diff = new_stock - product.stock_quantity
                            StockMovement.objects.create(
                                user=request.user,
                                product=product,
                                change=diff,
                                movement_type='manual',
                                note='Массовое редактирование'
                            )
                            product.stock_quantity = new_stock
                            changed = True
                            
                        if changed:
                            product.save()
                            updated_count += 1
                except (ValueError, TypeError):
                    continue
        
        messages.success(request, f'Обновлено {updated_count} товаров')
        return redirect('product_list')

    categories = Category.objects.filter(user=request.user)
    context = {
        'products': products_qs[:100],  # Limit to 100 for performance
        'categories': categories,
        'category_id': category_id,
        'query': query,
    }
    return render(request, 'catalog/bulk_edit.html', context)


@login_required
def bulk_price_change(request):
    """Raise or lower purchase prices for a brand or category by a percentage."""
    categories = Category.objects.filter(user=request.user)
    brands = Product.objects.filter(user=request.user).values_list('brand', flat=True).distinct().order_by('brand')
    brands = [b for b in brands if b]

    if request.method == 'POST':
        filter_type = request.POST.get('filter_type')  # 'brand' or 'category'
        brand = request.POST.get('brand', '').strip()
        category_id = request.POST.get('category_id', '').strip()
        percent_str = request.POST.get('percent', '0').replace(',', '.').strip()

        try:
            percent = float(percent_str)
        except (ValueError, TypeError):
            messages.error(request, 'Неверный процент')
            return redirect('bulk_price_change')

        if percent == 0:
            messages.warning(request, 'Процент изменения равен 0 — ничего не изменено')
            return redirect('bulk_price_change')

        qs = Product.objects.filter(user=request.user)
        label = ''
        if filter_type == 'brand' and brand:
            qs = qs.filter(brand__iexact=brand)
            label = f'бренд «{brand}»'
        elif filter_type == 'category' and category_id:
            qs = qs.filter(category_id=category_id)
            cat = Category.objects.filter(pk=category_id, user=request.user).first()
            label = f'категория «{cat.name if cat else category_id}»'
        else:
            messages.error(request, 'Выберите бренд или категорию')
            return redirect('bulk_price_change')

        count = qs.count()
        if count == 0:
            messages.warning(request, 'Нет товаров для этого фильтра')
            return redirect('bulk_price_change')

        from decimal import Decimal as D
        multiplier = D('1') + D(str(percent)) / D('100')

        from django.db.models import F
        from django.db.models.functions import Cast
        import django.db.models as dm
        # Update in Python loop for DecimalField precision
        for product in qs:
            product.price_purchase = (product.price_purchase * multiplier).quantize(D('0.01'))
            product.save(update_fields=['price_purchase'])

        sign = '+' if percent > 0 else ''
        messages.success(
            request,
            f'Изменено {count} товаров ({label}): {sign}{percent}% к закупочной цене'
        )
        return redirect('product_list')

    return render(request, 'catalog/bulk_price_change.html', {
        'categories': categories,
        'brands': brands,
    })


@login_required
def category_list(request):
    """List and manage categories."""
    categories = Category.objects.filter(user=request.user).annotate(product_count=models.Count('products'))

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, 'Категория создана')
            return redirect('category_list')
    else:
        form = CategoryForm()

    return render(request, 'catalog/categories.html', {'categories': categories, 'form': form})


@login_required
def category_delete(request, pk):
    """Delete a category."""
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Категория удалена')
    return redirect('category_list')


# ═══════════════════════════════════════════
# PRICE LEVELS
# ═══════════════════════════════════════════

@login_required
def price_level_list(request):
    """Manage price markup levels."""
    PriceLevel.create_defaults(request.user)
    levels = PriceLevel.objects.filter(user=request.user)

    if request.method == 'POST':
        form = PriceLevelForm(request.POST)
        if form.is_valid():
            level = form.save(commit=False)
            level.user = request.user
            level.save()
            # If this is set as default, unset others
            if level.is_default:
                PriceLevel.objects.filter(user=request.user).exclude(pk=level.pk).update(is_default=False)
            messages.success(request, f'Уровень цены "{level.name}" создан')
            return redirect('price_level_list')
    else:
        form = PriceLevelForm()

    # Show example prices
    sample_product = Product.objects.filter(user=request.user).first()
    levels_with_example = []
    for level in levels:
        example_price = level.calculate_price(sample_product.price_purchase) if sample_product else None
        levels_with_example.append({
            'level': level,
            'example_price': example_price,
        })

    context = {
        'levels_data': levels_with_example,
        'form': form,
        'sample_product': sample_product,
    }
    return render(request, 'catalog/price_levels.html', context)


@login_required
def price_level_edit(request, pk):
    """Edit a price level."""
    level = get_object_or_404(PriceLevel, pk=pk, user=request.user)

    if request.method == 'POST':
        form = PriceLevelForm(request.POST, instance=level)
        if form.is_valid():
            level = form.save()
            if level.is_default:
                PriceLevel.objects.filter(user=request.user).exclude(pk=level.pk).update(is_default=False)
            messages.success(request, f'Уровень "{level.name}" обновлен')
            return redirect('price_level_list')
    else:
        form = PriceLevelForm(instance=level)

    return render(request, 'catalog/price_level_form.html', {'form': form, 'level': level})


@login_required
def price_level_delete(request, pk):
    """Delete a price level."""
    level = get_object_or_404(PriceLevel, pk=pk, user=request.user)
    if request.method == 'POST':
        name = level.name
        level.delete()
        messages.success(request, f'Уровень "{name}" удален')
    return redirect('price_level_list')


# ═══════════════════════════════════════════
# CAR MATRIX & BARCODES
# ═══════════════════════════════════════════

@login_required
def car_matrix_list(request):
    """Manage car makes and models."""
    makes = CarMake.objects.filter(user=request.user).prefetch_related('models')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_make':
            name = request.POST.get('name', '').strip()
            if name:
                CarMake.objects.create(user=request.user, name=name)
                messages.success(request, f'Марка "{name}" добавлена')
        
        elif action == 'add_model':
            make_id = request.POST.get('make_id')
            name = request.POST.get('name', '').strip()
            if make_id and name:
                make = get_object_or_404(CarMake, pk=make_id, user=request.user)
                CarModel.objects.create(user=request.user, make=make, name=name)
                messages.success(request, f'Модель "{name}" добавлена для {make.name}')
        
        elif action == 'delete_make':
            pk = request.POST.get('pk')
            make = get_object_or_404(CarMake, pk=pk, user=request.user)
            make.delete()
            messages.success(request, 'Марка удалена')
            
        elif action == 'delete_model':
            pk = request.POST.get('pk')
            model = get_object_or_404(CarModel, pk=pk, user=request.user)
            model.delete()
            messages.success(request, 'Модель удалена')

        return redirect('car_matrix_list')

    return render(request, 'catalog/car_matrix.html', {'makes': makes})


@login_required
def print_price_tags(request):
    """Bulk print 58×40mm price labels for selected products."""
    product_ids = request.GET.getlist('ids')
    category_id = request.GET.get('category')
    brand = request.GET.get('brand', '').strip()

    products_qs = Product.objects.filter(user=request.user, is_active=True)
    if product_ids:
        products_qs = products_qs.filter(pk__in=product_ids)
    elif category_id:
        products_qs = products_qs.filter(category_id=category_id)
    elif brand:
        products_qs = products_qs.filter(brand__iexact=brand)
    else:
        products_qs = products_qs.none()

    products = list(products_qs[:200])
    for p in products:
        p.barcode_val = p.barcode or p.oem_number or str(p.pk)
        p.price_display = p.get_price()

    return render(request, 'catalog/print_price_tags.html', {'products': products})


@login_required
def print_barcode(request, pk):
    """Render a 58x40mm label for a product."""
    product = get_object_or_404(Product, pk=pk, user=request.user)
    # If no barcode, we might use OEM or PK
    barcode_val = product.barcode or product.oem_number or str(product.pk)
    
    context = {
        'product': product,
        'barcode_val': barcode_val,
        'price': product.get_price(),
    }
    return render(request, 'catalog/barcode_label.html', context)
