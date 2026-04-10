"""
Users URL patterns.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('search/', views.global_search, name='global_search'),
    path('backup/', views.backup_db, name='backup_db'),
    path('superadmin/', views.superadmin_panel, name='superadmin_panel'),
    path('superadmin/user/<int:user_id>/', views.superadmin_user_data, name='superadmin_user_data'),
    path('employees/', views.employee_list, name='employee_list'),
]
