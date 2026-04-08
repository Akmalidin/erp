from django.urls import path
from . import views

urlpatterns = [
    path('status/',          views.desktop_status,   name='desktop_status'),
    path('sync/',            views.desktop_sync,     name='desktop_sync'),
    path('pending-imports/', views.pending_imports,  name='desktop_pending_imports'),
]
