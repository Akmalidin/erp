from django.urls import path
from sync_views import sync_run, sync_status

urlpatterns = [
    path('run/', sync_run, name='sync_run'),
    path('status/', sync_status, name='sync_status'),
]
