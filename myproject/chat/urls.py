from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('room/<int:room_id>/', views.room_detail, name='room_detail'),
    path('create-room/', views.create_room, name='create_room'),
    path('room/<int:room_id>/delete/', views.delete_room, name='delete_room'),
    
    # Админ URLs
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/ban_user/', views.admin_ban_user, name='admin_ban_user'),
    path('admin/clear_messages/', views.admin_clear_old_messages, name='admin_clear_messages'),
    
    # API URLs
    path('room/<int:room_id>/send_message/', views.send_message, name='send_message'),
]
