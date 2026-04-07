"""
Catalog URL patterns.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('create/', views.product_create, name='product_create'),
    path('import/', views.product_import, name='product_import'),
    path('import/mapping/', views.product_import_mapping, name='product_import_mapping'),
    path('import/preview/', views.product_import_preview, name='product_import_preview'),
    path('import/process/', views.product_import_process, name='product_import_process'),
    path('import/history/', views.import_history_list, name='import_history_list'),
    path('import/history/<int:pk>/', views.import_history_detail, name='import_history_detail'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('print-price/', views.print_price_list, name='print_price_list'),
    path('print-tags/', views.print_price_tags, name='print_price_tags'),
    # Bulk Edit
    path('bulk-edit/', views.product_bulk_edit, name='product_bulk_edit'),
    path('bulk-price/', views.bulk_price_change, name='bulk_price_change'),
    # Price Levels
    path('price-levels/', views.price_level_list, name='price_level_list'),
    path('price-levels/<int:pk>/edit/', views.price_level_edit, name='price_level_edit'),
    path('price-levels/<int:pk>/delete/', views.price_level_delete, name='price_level_delete'),
    # Product detail/edit/delete (keep last — <int:pk> catches everything)
    path('car-matrix/', views.car_matrix_list, name='car_matrix_list'),
    path('car-matrix/make/<int:pk>/', views.car_make_detail, name='car_make_detail'),
    path('car-matrix/model/<int:pk>/', views.car_model_detail, name='car_model_detail'),
    path('<int:pk>/', views.product_detail, name='product_detail'),
    path('<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('<int:pk>/print-barcode/', views.print_barcode, name='print_barcode'),
]
