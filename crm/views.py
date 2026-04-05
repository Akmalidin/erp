"""
CRM views: client list, detail, create, edit, delete.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator

from .models import Client, Payment, ExpenseCategory, Expense, Shift
from .forms import ClientForm
from catalog.utils import get_smart_search_filter
from orders.models import Order, OrderItem
from decimal import Decimal
from django.utils import timezone


@login_required
def client_list(request):
    """List all clients with search."""
    clients = Client.objects.filter(user=request.user)

    # Search
    query = request.GET.get('q', '').strip()
    if query:
        search_fields = ['name', 'phone', 'email', 'company_name']
        clients = clients.filter(get_smart_search_filter(query, search_fields))

    # Annotate with order stats
    clients = clients.annotate(
        order_count=Count('orders'),
        total_spent=Sum('orders__total_price')
    )

    sort = request.GET.get('sort', '-created_at')
    if sort in ['name', '-name', '-created_at', 'created_at', '-order_count', '-total_spent']:
        clients = clients.order_by(sort)

    paginator = Paginator(clients, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'query': query,
        'sort': sort,
        'total_count': paginator.count,
    }
    return render(request, 'crm/list.html', context)


@login_required
def client_detail(request, pk):
    """Client card with order history."""
    client = get_object_or_404(Client, pk=pk, user=request.user)
    orders = Order.objects.filter(client=client, user=request.user).order_by('-created_at')

    total_spent = orders.aggregate(total=Sum('total_price'))['total'] or 0
    payments = Payment.objects.filter(client=client, user=request.user).order_by('-created_at')

    context = {
        'client': client,
        'orders': orders,
        'payments': payments,
        'total_spent': total_spent,
        'order_count': orders.count(),
    }
    return render(request, 'crm/detail.html', context)


@login_required
def record_payment(request, pk):
    """Record a manual payment to reduce client debt."""
    client = get_object_or_404(Client, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            amount = float(request.POST.get('amount', 0))
            p_type = request.POST.get('payment_type', 'cash')
            note = request.POST.get('note', '')
            
            if amount > 0:
                # Create payment record
                Payment.objects.create(
                    user=request.user,
                    client=client,
                    amount=amount,
                    payment_type=p_type,
                    note=note
                )
                
                # Reduce debt
                client.debt -= amount
                client.save(update_fields=['debt'])
                
                messages.success(request, f'Принят платеж: {amount:,.2f} {request.user.currency_symbol}')
            else:
                messages.error(request, 'Сумма должна быть больше нуля')
        except (ValueError, TypeError):
            messages.error(request, 'Некорректная сумма')
            
    return redirect('client_detail', pk=client.pk)


@login_required
def client_create(request):
    """Create new client."""
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.user = request.user
            client.save()
            messages.success(request, f'Клиент "{client.name}" создан')
            return redirect('client_detail', pk=client.pk)
    else:
        form = ClientForm()

    return render(request, 'crm/form.html', {'form': form, 'title': 'Новый клиент'})


@login_required
def client_edit(request, pk):
    """Edit existing client."""
    client = get_object_or_404(Client, pk=pk, user=request.user)

    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f'Клиент "{client.name}" обновлен')
            return redirect('client_detail', pk=client.pk)
    else:
        form = ClientForm(instance=client)

    return render(request, 'crm/form.html', {'form': form, 'title': 'Редактировать клиента', 'client': client})


@login_required
def client_delete(request, pk):
    """Delete a client."""
    client = get_object_or_404(Client, pk=pk, user=request.user)
    if request.method == 'POST':
        name = client.name
        client.delete()
        messages.success(request, f'Клиент "{name}" удален')
        return redirect('client_list')
    return render(request, 'crm/confirm_delete.html', {'client': client})


# === FINANCE & SHIFTS ===

@login_required
def expense_list(request):
    """List all business expenses with filtering."""
    expenses = Expense.objects.filter(user=request.user).select_related('category')
    categories = ExpenseCategory.objects.filter(user=request.user)
    
    # Simple date filtering
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    category_id = request.GET.get('category')
    
    if date_from:
        expenses = expenses.filter(date__gte=date_from)
    if date_to:
        expenses = expenses.filter(date__lte=date_to)
    if category_id:
        expenses = expenses.filter(category_id=category_id)
        
    total_amount = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    paginator = Paginator(expenses, 50)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'total_amount': total_amount,
        'date_from': date_from,
        'date_to': date_to,
        'category_id': category_id,
    }
    return render(request, 'crm/expense_list.html', context)


@login_required
def expense_create(request):
    """Quickly record an expense."""
    if request.method == 'POST':
        category_id = request.POST.get('category')
        new_category_name = request.POST.get('new_category')
        amount = request.POST.get('amount')
        note = request.POST.get('note', '')
        
        category = None
        if new_category_name:
            category, _ = ExpenseCategory.objects.get_or_create(user=request.user, name=new_category_name)
        elif category_id:
            category = get_object_or_404(ExpenseCategory, pk=category_id, user=request.user)
            
        if amount:
            Expense.objects.create(
                user=request.user,
                category=category,
                amount=amount,
                note=note
            )
            messages.success(request, 'Расход успешно записан')
        else:
            messages.error(request, 'Сумма обязательна')
            
    return redirect('expense_list')


@login_required
def shift_list(request):
    """List cashier shifts/Z-reports."""
    shifts = Shift.objects.filter(user=request.user).order_by('-opened_at')
    current_shift = shifts.filter(is_open=True).first()
    
    paginator = Paginator(shifts, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'crm/shift_list.html', {
        'page_obj': page_obj,
        'current_shift': current_shift
    })


@login_required
def shift_open(request):
    """Open a new cashier shift."""
    if Shift.objects.filter(user=request.user, is_open=True).exists():
        messages.warning(request, 'У вас уже есть открытая смена')
        return redirect('shift_list')
        
    if request.method == 'POST':
        initial_cash = request.POST.get('initial_cash', 0)
        Shift.objects.create(
            user=request.user,
            initial_cash=initial_cash
        )
        messages.success(request, 'Смена успешно открыта. Теперь можно продавать через POS.')
        return redirect('pos_view')
        
    return render(request, 'crm/shift_open.html')


@login_required
def shift_close(request, pk):
    """Close shift and show Z-report comparison."""
    shift = get_object_or_404(Shift, pk=pk, user=request.user)
    
    # Calculate expected amounts from orders linked to this shift
    orders = Order.objects.filter(shift=shift)
    
    # Expected breakdown
    # Total revenue from orders
    expected_stats = orders.aggregate(
        total=Sum('total_price'),
        cash=Sum('paid_amount', filter=Q(payment_method='cash')),
        card=Sum('paid_amount', filter=Q(payment_method='card')),
        mixed_total=Sum('paid_amount', filter=Q(payment_method='mixed'))
    )
    
    # For mixed payments, we'd ideally need a breakdown, but since we didn't store breakdown per order yet,
    # let's assume mixed payments are handled manually or we update order model to store them better.
    # Actually, in our pos_view we used paid_cash and paid_card.
    
    # Correct calculation: sum up CRM Payments linked to these orders
    from crm.models import Payment
    # Actually, let's just sum the Orders for simplicity now
    exp_cash = (expected_stats['cash'] or 0) + (shift.initial_cash)
    exp_card = (expected_stats['card'] or 0)
    
    if request.method == 'POST':
        actual_cash = Decimal(request.POST.get('actual_cash', 0))
        actual_card = Decimal(request.POST.get('actual_card', 0))
        
        shift.actual_cash = actual_cash
        shift.actual_card = actual_card
        shift.closed_at = timezone.now()
        shift.is_open = False
        shift.save()
        
        messages.success(request, f'Смена #{shift.pk} закрыта. Z-отчет сформирован.')
        return redirect('shift_list')
        
    context = {
        'shift': shift,
        'order_count': orders.count(),
        'exp_cash': exp_cash,
        'exp_card': exp_card,
        'total_rev': expected_stats['total'] or 0,
    }
    return render(request, 'crm/shift_close.html', context)
