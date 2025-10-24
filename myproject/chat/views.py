from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
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
            user = form.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}! Регистрация прошла успешно.')
            return redirect('home')
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
                login(request, user)
                messages.success(request, f'С возвращением, {username}!')
                return redirect('home')
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
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if name and len(name.strip()) > 0:
            try:
                room = ChatRoom.objects.create(
                    name=name.strip(),
                    description=description.strip(),
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
        else:
            messages.error(request, 'Название комнаты не может быть пустым.')
    
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
    # Простая логика для активных сессий (пользователи, заходившие за последние 24 часа)
    from datetime import datetime, timedelta
    active_sessions = User.objects.filter(
        last_login__gte=datetime.now() - timedelta(hours=24)
    ).count()
    
    # Статистика по комнатам
    top_rooms = ChatRoom.objects.annotate(
        message_count=Count('chatmessage'),
        user_count=Count('roommember')
    ).order_by('-message_count')[:5]
    
    context = {
        'total_rooms': total_rooms,
        'total_users': total_users,
        'active_sessions': active_sessions,
        'top_rooms': top_rooms,
    }
    return render(request, 'admin_dashboard.html', context)

@user_passes_test(lambda u: u.is_staff)
def admin_ban_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
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
            from datetime import datetime, timedelta
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

# API views
@login_required
def send_message(request, room_id):
    if request.method == 'POST':
        room = get_object_or_404(ChatRoom, id=room_id)
        message_text = request.POST.get('message') or request.JSON.get('content', '')
        
        if message_text and len(message_text.strip()) > 0:
            # Проверяем, является ли пользователь участником комнаты
            if not RoomMember.objects.filter(user=request.user, room=room).exists():
                return JsonResponse({'success': False, 'error': 'Вы не участник этой комнаты'})
            
            try:
                message = ChatMessage.objects.create(
                    room=room,
                    user=request.user,
                    message=message_text.strip()
                )
                return JsonResponse({
                    'success': True, 
                    'message_id': message.id,
                    'username': request.user.username,
                    'timestamp': message.timestamp.strftime('%H:%M')
                })
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        else:
            return JsonResponse({'success': False, 'error': 'Сообщение не может быть пустым'})
    
    return JsonResponse({'success': False, 'error': 'Неверный метод запроса'})

@login_required
def get_room_messages(request, room_id):
    if request.method == 'GET':
        room = get_object_or_404(ChatRoom, id=room_id)
        limit = int(request.GET.get('limit', 50))
        
        messages = ChatMessage.objects.filter(room=room).order_by('-timestamp')[:limit]
        
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
            'messages': list(reversed(messages_data))  # Возвращаем в правильном порядке
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

# Вспомогательные views
@login_required
def user_profile(request):
    user_rooms = RoomMember.objects.filter(user=request.user).select_related('room')
    user_messages = ChatMessage.objects.filter(user=request.user).count()
    
    context = {
        'user_rooms': user_rooms,
        'user_messages': user_messages,
    }
    return render(request, 'user_profile.html', context)

def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)
