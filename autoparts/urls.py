"""
Main URL configuration for AutoParts CRM.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('catalog/', include('catalog.urls')),
    path('warehouse/', include('warehouse.urls')),
    path('orders/', include('orders.urls')),
    path('crm/', include('crm.urls')),
    path('reports/', include('reports.urls')),
    path('purchases/', include('purchases.urls')),
    path('portal/', include('portal.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
