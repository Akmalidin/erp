from django.urls import path
from . import views

urlpatterns = [
    path('', views.purchase_list, name='purchase_list'),
    path('create/', views.purchase_create, name='purchase_create'),
    path('<int:pk>/', views.purchase_detail, name='purchase_detail'),
    path('<int:pk>/confirm/', views.purchase_confirm, name='purchase_confirm'),
    path('<int:pk>/cancel/', views.purchase_cancel, name='purchase_cancel'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),
    path('api/products/', views.product_search_api, name='purchase_product_search'),
    path('add-product/<int:product_pk>/', views.add_product_to_purchase, name='add_product_to_purchase'),
    path('auto-create/', views.auto_purchase_create, name='auto_purchase_create'),
    path('<int:pk>/import/', views.purchase_import, name='purchase_import'),
]
