
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib import messages

def register_view(request):
    if request.user.is_authenticated:
        messages.info(request, 'Вы уже авторизованы!')
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        # Валидация
        errors = []
        
        if not username:
            errors.append('Имя пользователя обязательно.')
        
        if not password1:
            errors.append('Пароль обязателен.')
        
        if not password2:
            errors.append('Подтверждение пароля обязательно.')
        
        if password1 != password2:
            errors.append('Пароли не совпадают.')
        
        if len(password1) < 8:
            errors.append('Пароль должен содержать минимум 8 символов.')
        
        if User.objects.filter(username=username).exists():
            errors.append('Пользователь с таким именем уже существует.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'register.html')
        
        try:
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

def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы.')
    return redirect('home')
