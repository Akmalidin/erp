"""
Reports views: sales by period, popular products, stock overview.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta, datetime

from orders.models import Order, OrderItem
from catalog.models import Product, PriceLevel
from crm.models import Client, Expense
from decimal import Decimal


@login_required
def reports_index(request):
    """Main reports dashboard."""
    # Date range filter
    period = request.GET.get('period', '30')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    today = timezone.now()

    if date_from and date_to:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            end_date = datetime.strptime(date_to, '%Y-%m-%d')
            start_date = timezone.make_aware(start_date)
            end_date = timezone.make_aware(end_date.replace(hour=23, minute=59, second=59))
        except (ValueError, TypeError):
            start_date = today - timedelta(days=30)
            end_date = today
    else:
        days = int(period) if period.isdigit() else 30
        start_date = today - timedelta(days=days)
        end_date = today

    # === SALES REPORT ===
    orders_in_period = Order.objects.filter(
        user=request.user,
        created_at__gte=start_date,
        created_at__lte=end_date,
    ).exclude(status='cancelled')

    total_sales = orders_in_period.aggregate(total=Sum('total_price'))['total'] or 0
    order_count = orders_in_period.count()
    avg_order = total_sales / order_count if order_count > 0 else 0

    # Sales by day
    sales_by_day = (
        orders_in_period
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(total=Sum('total_price'), count=Count('id'))
        .order_by('date')
    )

    # === TOP PRODUCTS ===
    top_products = (
        OrderItem.objects.filter(
            order__user=request.user,
            order__created_at__gte=start_date,
            order__created_at__lte=end_date,
        ).exclude(order__status='cancelled')
        .values('product__name', 'product__oem_number')
        .annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price')),
            total_profit=Sum(F('quantity') * (F('price') - F('product__price_purchase')))
        )
        .order_by('-total_qty')[:10]
    )

    total_profit = (
        OrderItem.objects.filter(
            order__user=request.user,
            order__created_at__gte=start_date,
            order__created_at__lte=end_date,
        ).exclude(order__status='cancelled')
        .aggregate(profit=Sum(F('quantity') * (F('price') - F('product__price_purchase'))))['profit'] or 0
    )

    # === EXPENSES & NET PROFIT ===
    total_expenses = Expense.objects.filter(
        user=request.user,
        date__gte=start_date.date(),
        date__lte=end_date.date()
    ).aggregate(total=Sum('amount'))['total'] or 0

    net_profit = float(total_profit) - float(total_expenses)

    # === SALES BY CATEGORY ===
    sales_by_category = (
        OrderItem.objects.filter(
            order__user=request.user,
            order__created_at__gte=start_date,
            order__created_at__lte=end_date,
        ).exclude(order__status='cancelled')
        .values('product__category__name')
        .annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price')),
            total_profit=Sum(F('quantity') * (F('price') - F('product__price_purchase')))
        )
        .order_by('-total_revenue')
    )

    # === SALES BY BRAND ===
    sales_by_brand = (
        OrderItem.objects.filter(
            order__user=request.user,
            order__created_at__gte=start_date,
            order__created_at__lte=end_date,
        ).exclude(order__status='cancelled')
        .values('product__brand')
        .annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price')),
            total_profit=Sum(F('quantity') * (F('price') - F('product__price_purchase')))
        )
        .order_by('-total_revenue')
    )

    # === STOCK REPORT ===
    all_products = Product.objects.filter(user=request.user, is_active=True)
    
    low_stock_products = all_products.filter(
        stock_quantity__lte=F('min_stock')
    ).order_by('stock_quantity')[:20]

    out_of_stock = all_products.filter(stock_quantity=0).count()
    low_stock_count = all_products.filter(
        stock_quantity__lte=5,
        stock_quantity__gt=0
    ).count()

    # Get default markup for retail calculation
    default_level = PriceLevel.get_default(request.user)
    markup = float(default_level.markup_percent) if default_level else 0.0
    
    # Capitalization
    # Since price_retail is a property, we calculate it in the query: purchase * (1 + markup/100)
    # Using float for faster/safer aggregation here if precision is not ultra-critical for a quick overview
    stock_stats = all_products.aggregate(
        total_purchase=Sum(F('stock_quantity') * F('price_purchase'))
    )
    stock_value_purchase = stock_stats['total_purchase'] or 0
    stock_value_retail = float(stock_value_purchase) * (1 + markup / 100)
    potential_profit = stock_value_retail - float(stock_value_purchase)

    # === TOP CLIENTS ===
    top_clients = (
        Client.objects.filter(
            user=request.user,
            orders__created_at__gte=start_date,
            orders__created_at__lte=end_date,
        ).exclude(orders__status='cancelled')
        .annotate(
            order_count=Count('orders'),
            total_spent=Sum('orders__total_price')
        )
        .order_by('-total_spent')[:10]
    )

    # === DEBTORS ===
    debtors = Client.objects.filter(user=request.user, debt__gt=0).order_by('-debt')
    total_debt = debtors.aggregate(total=Sum('debt'))['total'] or 0

    # === ORDER STATUS BREAKDOWN ===
    status_breakdown = (
        orders_in_period
        .values('status')
        .annotate(count=Count('id'), total=Sum('total_price'))
        .order_by('-count')
    )

    context = {
        'period': period,
        'date_from': start_date.strftime('%Y-%m-%d'),
        'date_to': end_date.strftime('%Y-%m-%d'),
        'total_sales': total_sales,
        'total_profit': total_profit,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'order_count': order_count,
        'avg_order': avg_order,
        'sales_by_day': list(sales_by_day),
        'sales_by_category': list(sales_by_category),
        'sales_by_brand': list(sales_by_brand),
        'top_products': list(top_products),
        'low_stock_products': low_stock_products,
        'out_of_stock': out_of_stock,
        'low_stock_count': low_stock_count,
        'stock_value_purchase': stock_value_purchase,
        'stock_value_retail': stock_value_retail,
        'potential_profit': potential_profit,
        'top_clients': list(top_clients),
        'debtors': debtors,
        'total_debt': total_debt,
        'status_breakdown': list(status_breakdown),
    }
    return render(request, 'reports/index.html', context)


@login_required
def abc_analysis(request):
    """
    ABC analysis of products by revenue.
    A — top products generating 80% of total revenue
    B — next 15% of revenue
    C — remaining 5%
    """
    period = request.GET.get('period', '365')
    today = timezone.now()
    days = int(period) if str(period).isdigit() else 365
    start_date = today - timedelta(days=days)

    # Aggregate revenue per product
    product_sales = (
        OrderItem.objects.filter(
            order__user=request.user,
            order__created_at__gte=start_date,
        ).exclude(order__status__in=['cancelled'])
        .values('product__id', 'product__name', 'product__oem_number', 'product__brand')
        .annotate(
            total_qty=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price')),
            total_profit=Sum(F('quantity') * (F('price') - F('product__price_purchase')))
        )
        .order_by('-total_revenue')
    )

    items = list(product_sales)
    if not items:
        return render(request, 'reports/abc.html', {
            'items': [], 'period': period,
            'total_a': 0, 'total_b': 0, 'total_c': 0,
        })

    grand_total = sum(float(i['total_revenue'] or 0) for i in items)
    if grand_total == 0:
        grand_total = 1

    cumulative = 0.0
    for item in items:
        rev = float(item['total_revenue'] or 0)
        cumulative += rev
        pct = (cumulative / grand_total) * 100
        item['revenue_pct'] = round(rev / grand_total * 100, 2)
        item['cumulative_pct'] = round(pct, 2)
        if pct <= 80:
            item['abc_group'] = 'A'
        elif pct <= 95:
            item['abc_group'] = 'B'
        else:
            item['abc_group'] = 'C'

    total_a = sum(1 for i in items if i['abc_group'] == 'A')
    total_b = sum(1 for i in items if i['abc_group'] == 'B')
    total_c = sum(1 for i in items if i['abc_group'] == 'C')

    return render(request, 'reports/abc.html', {
        'items': items,
        'period': period,
        'grand_total': grand_total,
        'total_a': total_a,
        'total_b': total_b,
        'total_c': total_c,
    })
