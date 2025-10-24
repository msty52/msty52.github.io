from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from datetime import datetime, timedelta
from .models import ChatRoom, ChatMessage, RoomMember
from .forms import CustomUserCreationForm, CustomAuthenticationForm

# Аутентификация
def register_view(request):
    # Если пользователь уже авторизован, перенаправляем на главную
    if request.user.is_authenticated:
        messages.info(request, 'Вы уже авторизованы!')
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.username}! Регистрация прошла успешно.')
                return redirect('home')
            except IntegrityError:
                messages.error(request, 'Пользователь с таким именем уже существует.')
            except Exception as e:
                messages.error(request, f'Произошла ошибка при регистрации: {str(e)}')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'register.html', {'form': form})

def login_view(request):
    # Если пользователь уже авторизован, перенаправляем на главную
    if request.user.is_authenticated:
        messages.info(request, 'Вы уже авторизованы!')
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'С возвращением, {username}!')
                    return redirect('home')
                else:
                    messages.error(request, 'Ваш аккаунт заблокирован.')
            else:
                messages.error(request, 'Неверное имя пользователя или пароль.')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'auth.html', {'form': form})

@login_required
def logout_view(request):
    username = request.user.username
    logout(request)
    messages.info(request, f'Вы успешно вышли из системы. До свидания, {username}!')
    return redirect('home')

# Основные views
def home(request):
    if request.user.is_authenticated:
        # Для авторизованных пользователей показываем комнаты
        rooms = ChatRoom.objects.annotate(
            participants_count=Count('roommember'),
            messages_count=Count('chatmessage')
        ).order_by('-created_at')
        return render(request, 'home.html', {'rooms': rooms})
    else:
        # Для неавторизованных показываем лендинг
        return render(request, 'home.html')

@login_required
def room_detail(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Добавляем пользователя в комнату если его там нет
    RoomMember.objects.get_or_create(user=request.user, room=room)
    
    # Получаем сообщения
    messages_list = ChatMessage.objects.filter(room=room).order_by('timestamp')[:50]
    
    # Статистика для комнаты
    stats = {
        'participants_count': RoomMember.objects.filter(room=room).count(),
        'messages_count': ChatMessage.objects.filter(room=room).count(),
        'links_count': ChatMessage.objects.filter(room=room, message__icontains='http').count(),
        'media_count': ChatMessage.objects.filter(room=room, message__icontains='[media]').count(),
        'files_count': ChatMessage.objects.filter(room=room, message__icontains='[file]').count(),
        'music_count': ChatMessage.objects.filter(room=room, message__icontains='[music]').count(),
        'voice_messages_count': ChatMessage.objects.filter(room=room, message__icontains='[voice]').count(),
    }
    
    context = {
        'room': room,
        'messages': messages_list,
        **stats
    }
    return render(request, 'room_detail.html', context)

@login_required
def create_room(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, 'Название комнаты не может быть пустым.')
            return render(request, 'create_room.html')
        
        if len(name) > 100:
            messages.error(request, 'Название комнаты слишком длинное (максимум 100 символов).')
            return render(request, 'create_room.html')
        
        try:
            # Проверяем, существует ли комната с таким именем
            if ChatRoom.objects.filter(name=name).exists():
                messages.error(request, 'Комната с таким названием уже существует.')
                return render(request, 'create_room.html')
                
            room = ChatRoom.objects.create(
                name=name,
                description=description,
                created_by=request.user
            )
            # Создатель автоматически становится участником
            RoomMember.objects.create(user=request.user, room=room)
            messages.success(request, f'Комната "{room.name}" успешно создана!')
            return redirect('room_detail', room_id=room.id)
            
        except IntegrityError:
            messages.error(request, 'Комната с таким названием уже существует.')
        except Exception as e:
            messages.error(request, f'Ошибка при создании комнаты: {str(e)}')
    
    return render(request, 'create_room.html')

@login_required
def delete_room(request, room_id):
    if request.method == 'POST':
        room = get_object_or_404(ChatRoom, id=room_id)
        
        # Проверяем права - только создатель или админ может удалить
        if request.user == room.created_by or request.user.is_staff:
            room_name = room.name
            room.delete()
            messages.success(request, f'Комната "{room_name}" успешно удалена.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('home')
        else:
            messages.error(request, 'У вас нет прав для удаления этой комнаты.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'No permission'})
            return redirect('room_detail', room_id=room_id)
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})

# Админские views
@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    total_rooms = ChatRoom.objects.count()
    total_users = User.objects.count()
    
    # Пользователи, заходившие за последние 24 часа
    active_sessions = User.objects.filter(
        last_login__gte=datetime.now() - timedelta(hours=24)
    ).count()
    
    # Статистика по комнатам
    top_rooms = ChatRoom.objects.annotate(
        message_count=Count('chatmessage'),
        user_count=Count('roommember')
    ).order_by('-message_count')[:5]
    
    # Последние зарегистрированные пользователи
    recent_users = User.objects.order_by('-date_joined')[:5]
    
    context = {
        'total_rooms': total_rooms,
        'total_users': total_users,
        'active_sessions': active_sessions,
        'top_rooms': top_rooms,
        'recent_users': recent_users,
    }
    return render(request, 'admin_dashboard.html', context)

@user_passes_test(lambda u: u.is_staff)
def admin_ban_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        if not username:
            return JsonResponse({'success': False, 'error': 'Имя пользователя не указано'})
        
        try:
            user = User.objects.get(username=username)
            if user == request.user:
                return JsonResponse({'success': False, 'error': 'Вы не можете заблокировать себя!'})
            
            user.is_active = False
            user.save()
            return JsonResponse({'success': True, 'message': f'Пользователь {username} заблокирован.'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
    
    return JsonResponse({'success': False, 'error': 'Неверный запрос'})

@user_passes_test(lambda u: u.is_staff)
def admin_unban_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        if not username:
            return JsonResponse({'success': False, 'error': 'Имя пользователя не указано'})
        
        try:
            user = User.objects.get(username=username)
            user.is_active = True
            user.save()
            return JsonResponse({'success': True, 'message': f'Пользователь {username} разблокирован.'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Пользователь не найден'})
    
    return JsonResponse({'success': False, 'error': 'Неверный запрос'})

@user_passes_test(lambda u: u.is_staff)
def admin_clear_old_messages(request):
    if request.method == 'POST':
        try:
            # Удаляем сообщения старше 30 дней
            old_date = datetime.now() - timedelta(days=30)
            deleted_count = ChatMessage.objects.filter(
                timestamp__lt=old_date
            ).delete()[0]
            
            return JsonResponse({
                'success': True, 
                'deleted_count': deleted_count,
                'message': f'Удалено {deleted_count} старых сообщений.'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный запрос'})

@user_passes_test(lambda u: u.is_staff)
def admin_user_list(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'admin_user_list.html', {'users': users})

@user_passes_test(lambda u: u.is_staff)
def admin_room_list(request):
    rooms = ChatRoom.objects.annotate(
        message_count=Count('chatmessage'),
        user_count=Count('roommember')
    ).order_by('-created_at')
    return render(request, 'admin_room_list.html', {'rooms': rooms})

@user_passes_test(lambda u: u.is_staff)
def admin_delete_user(request, user_id):
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)
            if user == request.user:
                messages.error(request, 'Вы не можете удалить свой аккаунт!')
            else:
                username = user.username
                user.delete()
                messages.success(request, f'Пользователь {username} удален.')
        except Exception as e:
            messages.error(request, f'Ошибка при удалении пользователя: {str(e)}')
    
    return redirect('admin_user_list')

# API views
@login_required
def send_message(request, room_id):
    if request.method == 'POST':
        room = get_object_or_404(ChatRoom, id=room_id)
        
        # Получаем текст сообщения из разных источников
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            message_text = data.get('content', '')
        else:
            message_text = request.POST.get('message', '')
        
        message_text = message_text.strip()
        
        if not message_text:
            return JsonResponse({'success': False, 'error': 'Сообщение не может быть пустым'})
        
        if len(message_text) > 1000:
            return JsonResponse({'success': False, 'error': 'Сообщение слишком длинное (максимум 1000 символов)'})
        
        # Проверяем, является ли пользователь участником комнаты
        if not RoomMember.objects.filter(user=request.user, room=room).exists():
            return JsonResponse({'success': False, 'error': 'Вы не участник этой комнаты'})
        
        try:
            message = ChatMessage.objects.create(
                room=room,
                user=request.user,
                message=message_text
            )
            return JsonResponse({
                'success': True, 
                'message_id': message.id,
                'username': request.user.username,
                'is_admin': request.user.is_staff,
                'timestamp': message.timestamp.strftime('%H:%M'),
                'message_content': message_text
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
def get_room_messages(request, room_id):
    if request.method == 'GET':
        room = get_object_or_404(ChatRoom, id=room_id)
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        # Проверяем, является ли пользователь участником комнаты
        if not RoomMember.objects.filter(user=request.user, room=room).exists():
            return JsonResponse({'success': False, 'error': 'Доступ запрещен'})
        
        messages = ChatMessage.objects.filter(room=room).order_by('-timestamp')[offset:offset + limit]
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'username': msg.user.username,
                'message': msg.message,
                'timestamp': msg.timestamp.strftime('%H:%M'),
                'is_admin': msg.user.is_staff,
                'is_own': msg.user == request.user
            })
        
        return JsonResponse({
            'success': True,
            'messages': list(reversed(messages_data)),  # Возвращаем в правильном порядке
            'has_more': ChatMessage.objects.filter(room=room).count() > offset + limit
        })
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
def leave_room(request, room_id):
    if request.method == 'POST':
        room = get_object_or_404(ChatRoom, id=room_id)
        
        try:
            membership = RoomMember.objects.get(user=request.user, room=room)
            # Не позволяем создателю покинуть комнату
            if room.created_by == request.user:
                return JsonResponse({
                    'success': False, 
                    'error': 'Создатель не может покинуть комнату. Удалите комнату вместо этого.'
                })
            
            membership.delete()
            messages.info(request, f'Вы покинули комнату "{room.name}"')
            return JsonResponse({'success': True})
        except RoomMember.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Вы не участник этой комнаты'})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
def edit_room(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Проверяем права - только создатель или админ может редактировать
    if not (request.user == room.created_by or request.user.is_staff):
        messages.error(request, 'У вас нет прав для редактирования этой комнаты.')
        return redirect('room_detail', room_id=room_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, 'Название комнаты не может быть пустым.')
            return render(request, 'edit_room.html', {'room': room})
        
        try:
            # Проверяем, не занято ли имя другой комнатой
            if ChatRoom.objects.filter(name=name).exclude(id=room_id).exists():
                messages.error(request, 'Комната с таким названием уже существует.')
                return render(request, 'edit_room.html', {'room': room})
                
            room.name = name
            room.description = description
            room.save()
            
            messages.success(request, f'Комната "{room.name}" успешно обновлена!')
            return redirect('room_detail', room_id=room_id)
            
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении комнаты: {str(e)}')
    
    return render(request, 'edit_room.html', {'room': room})

# Вспомогательные views
@login_required
def user_profile(request):
    user_rooms = RoomMember.objects.filter(user=request.user).select_related('room')
    user_messages = ChatMessage.objects.filter(user=request.user).count()
    rooms_created = ChatRoom.objects.filter(created_by=request.user).count()
    
    context = {
        'user_rooms': user_rooms,
        'user_messages': user_messages,
        'rooms_created': rooms_created,
    }
    return render(request, 'user_profile.html', context)

@login_required
def update_profile(request):
    if request.method == 'POST':
        # Здесь можно добавить логику обновления профиля
        # Например, смену пароля, email и т.д.
        messages.info(request, 'Функция обновления профиля в разработке.')
    
    return redirect('user_profile')

# Обработчики ошибок
def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)

def handler403(request, exception):
    return render(request, '403.html', status=403)

def handler400(request, exception):
    return render(request, '400.html', status=400)

# Утилиты
@login_required
def search_rooms(request):
    query = request.GET.get('q', '').strip()
    if query:
        rooms = ChatRoom.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).annotate(
            participants_count=Count('roommember'),
            messages_count=Count('chatmessage')
        )[:20]
    else:
        rooms = ChatRoom.objects.none()
    
    return render(request, 'search_results.html', {
        'rooms': rooms,
        'query': query,
        'results_count': rooms.count()
    })

@login_required
def user_activity(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    # Показываем активность только для своего профиля или для админов
    if request.user != user and not request.user.is_staff:
        messages.error(request, 'У вас нет прав для просмотра этого профиля.')
        return redirect('home')
    
    user_messages = ChatMessage.objects.filter(user=user).order_by('-timestamp')[:50]
    user_rooms = RoomMember.objects.filter(user=user).select_related('room')
    
    context = {
        'profile_user': user,
        'user_messages': user_messages,
        'user_rooms': user_rooms,
        'total_messages': ChatMessage.objects.filter(user=user).count(),
    }
    return render(request, 'user_activity.html', context)
