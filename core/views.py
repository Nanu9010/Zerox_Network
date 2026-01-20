from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProfile


def home(request):
    """Landing page"""
    return render(request, 'core/home.html')


def signup(request):
    """User signup"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        role = request.POST.get('role', 'CUSTOMER')
        
        # Validation
        if password != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'core/signup.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'core/signup.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'core/signup.html')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Create profile
        UserProfile.objects.create(
            user=user,
            role=role,
            phone=phone
        )
        
        # Auto login
        login(request, user)
        messages.success(request, f'Welcome to Zerox, {username}!')
        
        # Redirect based on role
        if role == 'SHOP':
            return redirect('shops:register')
        else:
            return redirect('core:home')
    
    return render(request, 'core/signup.html')


def user_login(request):
    """User login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect to next or home
            next_url = request.GET.get('next', 'core:home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'core/login.html')


def user_logout(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('core:home')


@login_required
def dashboard_router(request):
    """Route user to appropriate dashboard based on role"""
    user = request.user
    
    if user.is_staff:
        # Admin
        return redirect('admin_portal:dashboard')
    
    # Check if Shop Owner
    try:
        if user.shop:
            return redirect('shops:dashboard')
    except:
        pass
        
    # Check Profile Role
    try:
        if user.profile.role == 'SHOP':
            return redirect('shops:register') # Or dashboard if shop exists (handled above)
    except:
        pass
        
    # Default Customer
    return redirect('orders:my_orders')

@login_required
def profile(request):
    """User profile page with edit functionality"""
    if request.method == 'POST':
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        
        # Simple validation
        if not email or not phone:
            messages.error(request, 'Email and phone are required.')
        else:
            user = request.user
            user.email = email
            user.save()
            
            profile = user.profile
            profile.phone = phone
            profile.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('core:profile')
            
    return render(request, 'core/profile.html')
