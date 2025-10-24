from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Основные URLs
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
    path('admin/unban_user/', views.admin_unban_user, name='admin_unban_user'),
    path('admin/clear_messages/', views.admin_clear_old_messages, name='admin_clear_messages'),
    path('admin/users/', views.admin_user_list, name='admin_user_list'),
    path('admin/rooms/', views.admin_room_list, name='admin_room_list'),
    
    # API URLs
    path('room/<int:room_id>/send_message/', views.send_message, name='send_message'),
    path('room/<int:room_id>/messages/', views.get_room_messages, name='get_room_messages'),
    path('room/<int:room_id>/leave/', views.leave_room, name='leave_room'),
    
    # Профиль
    path('profile/', views.user_profile, name='user_profile'),
]

# Обработчики ошибок
handler404 = views.handler404
handler500 = views.handler500
