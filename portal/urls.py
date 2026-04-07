from django.urls import path
from . import views

urlpatterns = [
    # Client portal
    path('', views.portal_dashboard, name='portal_dashboard'),
    path('login/', views.portal_login, name='portal_login'),
    path('logout/', views.portal_logout, name='portal_logout'),
    path('orders/<int:pk>/', views.portal_order_detail, name='portal_order_detail'),
    path('catalog/', views.portal_catalog, name='portal_catalog'),
    path('cart/', views.portal_cart_view, name='portal_cart'),
    path('cart/add/<int:product_id>/', views.portal_cart_add, name='portal_cart_add'),
    path('cart/remove/<int:product_id>/', views.portal_cart_remove, name='portal_cart_remove'),
    path('cart/checkout/', views.portal_checkout, name='portal_checkout'),

    # Admin-side portal management
    path('manage/<int:client_pk>/', views.admin_portal_manage, name='admin_portal_manage'),
    path('notifications/', views.admin_notifications, name='portal_notifications'),
    path('notifications/<int:pk>/read/', views.admin_mark_notification_read, name='portal_notification_read'),

    # Admin note reply
    path('notes/<int:note_pk>/reply/', views.admin_reply_note, name='admin_reply_note'),
]
