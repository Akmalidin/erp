from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_list, name='client_list'),
    path('create/', views.client_create, name='client_create'),
    path('<int:pk>/', views.client_detail, name='client_detail'),
    path('<int:pk>/edit/', views.client_edit, name='client_edit'),
    path('<int:pk>/delete/', views.client_delete, name='client_delete'),
    path('<int:pk>/payment/', views.record_payment, name='record_payment'),
    
    # Finance & Shifts
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('shifts/', views.shift_list, name='shift_list'),
    path('shifts/open/', views.shift_open, name='shift_open'),
    path('shifts/<int:pk>/close/', views.shift_close, name='shift_close'),
]
