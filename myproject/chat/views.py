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

def room_detail(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    
    # Статистика для комнаты
    stats = {
        'participants_count': room.participants.count(),
        'messages_count': room.messages.count(),
        'links_count': room.messages.filter(content__contains='http').count(),
        'media_count': room.messages.filter(content__contains='[media]').count(),
        'files_count': room.messages.filter(content__contains='[file]').count(),
        'music_count': room.messages.filter(content__contains='[music]').count(),
        'voice_messages_count': room.messages.filter(content__contains='[voice]').count(),
    }
    
    messages = room.messages.all().order_by('timestamp')[:50]
    
    context = {
        'room': room,
        'messages': messages,
        **stats
    }
    return render(request, 'room_detail.html', context)

@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    total_rooms = Room.objects.count()
    total_users = User.objects.count()
    active_sessions = 0  # Здесь можно добавить логику подсчета активных сессий
    
    context = {
        'total_rooms': total_rooms,
        'total_users': total_users,
        'active_sessions': active_sessions,
    }
    return render(request, 'admin_dashboard.html', context)

@user_passes_test(lambda u: u.is_staff)
def delete_room(request, room_id):
    if request.method == 'POST':
        room = get_object_or_404(Room, id=room_id)
        room.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

@user_passes_test(lambda u: u.is_staff)
def ban_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        user = get_object_or_404(User, username=username)
        user.is_active = False
        user.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def home(request):
    rooms = ChatRoom.objects.all()
    return render(request, 'chat/index.html', {
        'rooms': rooms,
    })

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('home')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'chat/auth.html', {
        'form': form,
        'auth_type': 'register'
    })

def login_view(request):
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
    
    return render(request, 'chat/auth.html', {
        'form': form,
        'auth_type': 'login'
    })

def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('home')

@login_required
def room_detail(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    room_messages = ChatMessage.objects.filter(room=room).order_by('timestamp')[:50]
    room_members = RoomMember.objects.filter(room=room)
    
    if request.method == 'POST':
        message_text = request.POST.get('message')
        
        if message_text:
            ChatMessage.objects.create(
                room=room,
                user=request.user,
                message=message_text
            )
            return redirect('room_detail', room_id=room_id)
    
    return render(request, 'chat/room_detail.html', {
        'room': room,
        'messages': room_messages,
        'room_members': room_members,
    })

@login_required
def create_room(request):
    error_message = None
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if name:
            try:
                room = ChatRoom.objects.create(
                    name=name,
                    description=description or '',
                    created_by=request.user
                )
                messages.success(request, f'Комната "{name}" успешно создана!')
                return redirect('room_detail', room_id=room.id)
                
            except IntegrityError:
                error_message = f'Комната с названием "{name}" уже существует. Выберите другое название.'
    
    return render(request, 'chat/create_room.html', {
        'error_message': error_message,
    })

@login_required
def delete_room(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    room_name = room.name
    
    if request.method == 'POST':
        # Проверяем, что пользователь - создатель комнаты
        if room.created_by == request.user or request.user.is_superuser:
            room.delete()
            messages.success(request, f'Комната "{room_name}" успешно удалена!')
            return redirect('home')
        else:
            messages.error(request, 'Вы можете удалять только свои комнаты.')
            return redirect('room_detail', room_id=room_id)
    
    return render(request, 'chat/delete_room.html', {
        'room': room,

    })

