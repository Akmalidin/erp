from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_index, name='reports_index'),
    path('abc/', views.abc_analysis, name='abc_analysis'),
]
