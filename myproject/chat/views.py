from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages

def register_view(request):
    if request.user.is_authenticated:
        messages.info(request, 'Вы уже авторизованы!')
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        # Базовая валидация
        if not username:
            messages.error(request, 'Имя пользователя обязательно.')
            return render(request, 'register.html')
        
        if not password1 or not password2:
            messages.error(request, 'Все поля пароля обязательны.')
            return render(request, 'register.html')
        
        if password1 != password2:
            messages.error(request, 'Пароли не совпадают.')
            return render(request, 'register.html')
        
        if len(password1) < 8:
            messages.error(request, 'Пароль должен содержать минимум 8 символов.')
            return render(request, 'register.html')
        
        try:
            # Проверяем, существует ли пользователь
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Пользователь с таким именем уже существует.')
                return render(request, 'register.html')
            
            # Создаем пользователя
            user = User.objects.create_user(
                username=username,
                password=password1
            )
            
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}! Регистрация прошла успешно.')
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f'Произошла ошибка при регистрации: {str(e)}')
    
    return render(request, 'register.html')

def login_view(request):
    if request.user.is_authenticated:
        messages.info(request, 'Вы уже авторизованы!')
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not username or not password:
            messages.error(request, 'Все поля обязательны.')
            return render(request, 'auth.html')
        
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
    
    return render(request, 'auth.html')
