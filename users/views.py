"""
User views: login, register, dashboard, logout.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

import shutil
import os
from .forms import LoginForm, RegisterForm, ProfileForm
from catalog.models import Product
from crm.models import Client
from orders.models import Order, OrderItem


def login_view(request):
    """User login page."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.first_name or user.email}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Неверный email или пароль')
    else:
        form = LoginForm()

    return render(request, 'users/login.html', {'form': form})


def register_view(request):
    """User registration page."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Аккаунт успешно создан!')
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'users/register.html', {'form': form})


def logout_view(request):
    """Logout user."""
    logout(request)
    messages.info(request, 'Вы вышли из системы')
    return redirect('login')


@login_required
def profile_view(request):
    """User profile edit page."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    
    return render(request, 'users/profile.html', {'form': form})


@login_required
def global_search(request):
    """Global search across products, orders and clients."""
    query = request.GET.get('q', '').strip()
    if not query:
        return render(request, 'users/search.html', {'query': '', 'products': [], 'orders': [], 'clients': []})

    from django.db.models import Q

    products = Product.objects.filter(
        user=request.user
    ).filter(
        Q(name__icontains=query) |
        Q(oem_number__icontains=query) |
        Q(part_number__icontains=query) |
        Q(barcode__icontains=query) |
        Q(brand__icontains=query)
    )[:15]

    orders_filter = Q(client__name__icontains=query) | Q(notes__icontains=query)
    if query.isdigit():
        orders_filter |= Q(pk=int(query))
    orders = Order.objects.filter(user=request.user).filter(orders_filter).select_related('client')[:10]

    clients = Client.objects.filter(
        user=request.user
    ).filter(
        Q(name__icontains=query) |
        Q(phone__icontains=query) |
        Q(company_name__icontains=query) |
        Q(email__icontains=query)
    )[:10]

    return render(request, 'users/search.html', {
        'query': query,
        'products': products,
        'orders': orders,
        'clients': clients,
    })


@login_required
def backup_db(request):
    """Create a backup copy of the SQLite database."""
    if request.method == 'POST':
        from django.conf import settings as django_settings
        from django.utils import timezone as tz
        db_path = str(django_settings.DATABASES['default'].get('NAME', ''))
        if not db_path or not os.path.exists(db_path):
            messages.error(request, 'База данных не найдена или используется не SQLite')
            return redirect('profile')

        backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = tz.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'db_backup_{timestamp}.sqlite3')
        shutil.copy2(db_path, backup_path)
        messages.success(request, f'Резервная копия сохранена: backups/db_backup_{timestamp}.sqlite3')
    return redirect('profile')


@login_required
def dashboard_view(request):
    """Main dashboard with statistics and recent activity."""
    today = timezone.now()
    month_ago = today - timedelta(days=30)
    week_ago = today - timedelta(days=7)

    # Key metrics
    total_products = Product.objects.filter(user=request.user).count()
    total_clients = Client.objects.filter(user=request.user).count()
    total_orders = Order.objects.filter(user=request.user).count()

    # Monthly sales
    monthly_sales = Order.objects.filter(
        user=request.user,
        created_at__gte=month_ago
    ).aggregate(total=Sum('total_price'))['total'] or 0

    # Weekly sales
    weekly_sales = Order.objects.filter(
        user=request.user,
        created_at__gte=week_ago
    ).aggregate(total=Sum('total_price'))['total'] or 0

    # Today's orders
    today_orders = Order.objects.filter(
        user=request.user,
        created_at__date=today.date()
    ).count()

    # Low stock products (less than 5)
    low_stock = Product.objects.filter(user=request.user, stock_quantity__lt=5).count()

    # Recent orders (last 10)
    recent_orders = Order.objects.filter(user=request.user).select_related('client').order_by('-created_at')[:10]

    # Sales chart data (last 30 days)
    sales_by_day = (
        Order.objects.filter(user=request.user, created_at__gte=month_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(total=Sum('total_price'), count=Count('id'))
        .order_by('date')
    )

    # Top products
    top_products = (
        OrderItem.objects.filter(order__user=request.user)
        .values('product__name')
        .annotate(total_qty=Sum('quantity'), total_sum=Sum('price'))
        .order_by('-total_qty')[:5]
    )

    context = {
        'total_products': total_products,
        'total_clients': total_clients,
        'total_orders': total_orders,
        'monthly_sales': monthly_sales,
        'weekly_sales': weekly_sales,
        'today_orders': today_orders,
        'low_stock': low_stock,
        'recent_orders': recent_orders,
        'sales_by_day': list(sales_by_day),
        'top_products': list(top_products),
    }
    return render(request, 'dashboard.html', context)


# ═══════════════════════════════════════════
# SUPERADMIN PANEL (только для владельца)
# ═══════════════════════════════════════════

SUPERADMIN_EMAIL = 'akmalmadakimov6@gmail.com'


def superadmin_required(view_func):
    """Decorator: only allow superadmin email."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.email != SUPERADMIN_EMAIL:
            messages.error(request, 'Доступ запрещен')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@superadmin_required
def superadmin_panel(request):
    """Owner control panel: manage all users."""
    from .models import User
    from catalog.models import Product
    from orders.models import Order
    from crm.models import Client

    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        target = User.objects.filter(pk=user_id).exclude(email=SUPERADMIN_EMAIL).first()

        if target:
            if action == 'block':
                target.is_active = False
                target.save(update_fields=['is_active'])
                messages.success(request, f'Пользователь {target.email} заблокирован')
            elif action == 'unblock':
                target.is_active = True
                target.save(update_fields=['is_active'])
                messages.success(request, f'Пользователь {target.email} разблокирован')
            elif action == 'set_password':
                new_pass = request.POST.get('new_password', '').strip()
                if new_pass and len(new_pass) >= 6:
                    target.set_password(new_pass)
                    target.save()
                    messages.success(request, f'Пароль для {target.email} изменён')
                else:
                    messages.error(request, 'Пароль должен быть минимум 6 символов')
        return redirect('superadmin_panel')

    users = User.objects.exclude(email=SUPERADMIN_EMAIL).order_by('-date_joined').annotate(
        product_count=Count('products', distinct=True),
        order_count=Count('orders', distinct=True),
        client_count=Count('clients', distinct=True),
    )

    context = {'users': users}
    return render(request, 'users/superadmin_panel.html', context)


@login_required
@superadmin_required
def superadmin_user_data(request, user_id):
    """View data for a specific user."""
    from .models import User
    from catalog.models import Product
    from orders.models import Order
    from crm.models import Client
    from purchases.models import Purchase

    target = get_object_or_404(User, pk=user_id)
    products = Product.objects.filter(user=target).order_by('-created_at')[:20]
    orders = Order.objects.filter(user=target).select_related('client').order_by('-created_at')[:20]
    clients = Client.objects.filter(user=target).order_by('name')[:20]

    context = {
        'target': target,
        'products': products,
        'orders': orders,
        'clients': clients,
    }
    return render(request, 'users/superadmin_user_data.html', context)
