from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('pos/', views.pos_view, name='pos_view'),
    path('create/', views.order_create, name='order_create'),
    path('api/products/', views.product_search_api, name='product_search_api'),
    path('<int:pk>/', views.order_detail, name='order_detail'),
    path('<int:pk>/edit/', views.order_edit, name='order_edit'),
    path('<int:pk>/status/', views.order_status_update, name='order_status_update'),
    path('quick-sale/<int:product_id>/', views.quick_sale, name='quick_sale'),
    path('<int:pk>/print/receipt/', views.print_receipt, name='print_receipt'),
    path('<int:pk>/print/invoice/', views.print_invoice, name='print_invoice'),
]
