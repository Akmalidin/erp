from django.urls import path
from . import views

urlpatterns = [
    path('', views.stock_list, name='stock_list'),
    path('movements/', views.movement_history, name='movement_history'),
    path('adjust/<int:pk>/', views.stock_adjust, name='stock_adjust'),
    path('bulk-add/', views.stock_bulk_add, name='stock_bulk_add'),
    path('inventory/', views.inventory_view, name='inventory_list'),
    path('locations/', views.warehouse_list, name='warehouse_list'),
    path('transfer/', views.stock_transfer, name='stock_transfer'),
]
