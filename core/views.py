from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import UserProfile, Notification
from shops.models import Shop


def propagate_user_details(user):
    """Propagate user detail changes to Shop and Order records"""
    new_name = user.get_full_name() or user.username
    new_phone = user.profile.phone if hasattr(user, 'profile') else ''
    new_email = user.email
    
    # Update all shops owned by this user
    if hasattr(user, 'shops'):
        user.shops.update(phone=new_phone)
    
    # Update all orders placed by this user
    if hasattr(user, 'orders'):
        user.orders.update(customer_name=new_name, customer_phone=new_phone)


def home(request):
    """Landing page"""
    return render(request, 'core/home.html')


def signup(request):
    """User signup - with optional shop creation"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        role = request.POST.get('role', 'CUSTOMER')
        is_shop_owner = request.POST.get('is_shop_owner') == 'on'
        
        # If "Both" selected, primary role = CUSTOMER, is_shop_owner = True
        if role == 'BOTH':
            role = 'CUSTOMER'
            is_shop_owner = True
        
        # If role is SHOP, force is_shop_owner
        if role == 'SHOP':
            is_shop_owner = True
        
        # Shop data (optional)
        shop_name = request.POST.get('shop_name', '').strip()
        shop_location = request.POST.get('shop_location', '').strip()
        shop_phone = request.POST.get('shop_phone', '').strip()
        shop_lat = request.POST.get('shop_lat')
        shop_lon = request.POST.get('shop_lon')
        a4_bw = request.POST.get('a4_bw_price', '1.00')
        a4_color = request.POST.get('a4_color_price', '5.00')
        a3_bw = request.POST.get('a3_bw_price', '2.00')
        a3_color = request.POST.get('a3_color_price', '10.00')
        
        # Determine if shop should be created
        create_shop = is_shop_owner and shop_name and shop_location and shop_phone
        
        # Validation
        errors = []
        if password != password2:
            errors.append('Passwords do not match.')
        if User.objects.filter(username=username).exists():
            errors.append('Username already taken.')
        if User.objects.filter(email=email).exists():
            errors.append('Email already registered.')
        if role == 'SHOP' and not create_shop:
            errors.append('Shop name, location, and phone are required for Shop Owner accounts.')
        
        if errors:
            for e in errors:
                messages.error(request, e)
            context = {'selected_role': role, 'is_shop_owner': is_shop_owner}
            return render(request, 'core/signup.html', context)
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Create profile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.is_shop_owner = is_shop_owner
        profile.phone = phone
        profile.save()
        
        # Create shop if details provided
        if create_shop:
            shop = Shop.objects.create(
                owner=user,
                name=shop_name,
                location=shop_location,
                phone=shop_phone,
                latitude=shop_lat if shop_lat else None,
                longitude=shop_lon if shop_lon else None,
                a4_bw_price=a4_bw,
                a4_color_price=a4_color,
                a3_bw_price=a3_bw,
                a3_color_price=a3_color,
                is_approved=False
            )
            messages.success(request, f'🏪 Shop "{shop_name}" registered! QR: {shop.qr_code}. Pending admin approval.')
        
        # Auto login
        login(request, user)
        messages.success(request, f'Welcome to Zerox, {username}!')
        
        # Redirect based on role
        if role == 'SHOP' and create_shop:
            return redirect('shops:dashboard')
        elif is_shop_owner:
            return redirect('core:choose_dashboard')
        else:
            return redirect('orders:my_orders')
    
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
            
            # Redirect based on user role via dashboard router
            next_url = request.GET.get('next')
            if next_url and next_url != '/':
                return redirect(next_url)
            return redirect('core:dashboard')
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
    
    # Check Profile Role first — role is the source of truth
    try:
        if hasattr(user, 'profile'):
            role = user.profile.role
            
            # SHOP role → always go to shop portal (never admin)
            if role == 'SHOP':
                if user.shops.exists():
                    return redirect('shops:dashboard')
                return redirect('shops:register')
            
            # ADMIN/STAFF role → admin portal
            if role in ['ADMIN', 'STAFF'] and (user.is_staff or user.is_superuser):
                return redirect('admin_portal:dashboard')
            
            # CUSTOMER role + is_shop_owner → unified dashboard
            if role == 'CUSTOMER' and user.profile.is_shop_owner:
                return redirect('core:my_dashboard')
    except Exception:
        pass
    
    # Check if Shop Owner via shops relation (fallback)
    try:
        if user.shops.exists():
            return redirect('shops:dashboard')
    except Exception:
        pass

    try:
        if hasattr(user, 'shop') and user.shop:
            return redirect('shops:dashboard')
    except Exception:
        pass
        
    # Default Customer
    return redirect('orders:my_orders')

@login_required
def profile(request):
    """User profile page with edit functionality"""
    user_profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'role': 'ADMIN' if request.user.is_superuser else ('STAFF' if request.user.is_staff else 'CUSTOMER'),
            'phone': ''
        }
    )
    user_shops = request.user.shops.all() if hasattr(request.user, 'shops') else Shop.objects.none()
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'profile')
        
        if form_type == 'shop':
            # Handle shop creation from profile
            shop_name = request.POST.get('shop_name', '').strip()
            shop_location = request.POST.get('shop_location', '').strip()
            shop_phone = request.POST.get('shop_phone', '').strip()
            shop_lat = request.POST.get('shop_lat')
            shop_lon = request.POST.get('shop_lon')
            a4_bw = request.POST.get('a4_bw_price', '1.00')
            a4_color = request.POST.get('a4_color_price', '5.00')
            a3_bw = request.POST.get('a3_bw_price', '2.00')
            a3_color = request.POST.get('a3_color_price', '10.00')
            
            if shop_name and shop_location and shop_phone:
                shop = Shop.objects.create(
                    owner=request.user,
                    name=shop_name,
                    location=shop_location,
                    phone=shop_phone,
                    latitude=shop_lat if shop_lat else None,
                    longitude=shop_lon if shop_lon else None,
                    a4_bw_price=a4_bw,
                    a4_color_price=a4_color,
                    a3_bw_price=a3_bw,
                    a3_color_price=a3_color,
                    is_approved=False
                )
                user_profile.is_shop_owner = True
                user_profile.save()
                propagate_user_details(request.user)
                messages.success(request, f'🏪 Shop "{shop_name}" registered! QR: {shop.qr_code}. Pending admin approval.')
            else:
                messages.error(request, 'Shop name, location, and phone are required.')
            return redirect('core:profile')
        
        else:
            # Handle profile update
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            
            if not email or not phone:
                messages.error(request, 'Email and phone are required.')
            else:
                user = request.user
                user.email = email
                user.save()
                
                user_profile.phone = phone
                user_profile.save()
                
                propagate_user_details(user)
                
                messages.success(request, 'Profile updated successfully!')
                return redirect('core:profile')
            
    context = {
        'user_shops': user_shops,
    }
    return render(request, 'core/profile.html', context)


@login_required
def my_dashboard(request):
    """Unified dashboard for CUSTOMER + is_shop_owner users — shows orders, shops, notifications"""
    from orders.models import Order
    
    user = request.user
    user_shops = user.shops.all()
    
    # Recent orders
    orders = Order.objects.filter(customer=user).order_by('-created_at')[:10]
    
    # Order stats
    total_orders = Order.objects.filter(customer=user).count()
    active_orders = Order.objects.filter(customer=user, status__in=['PAID', 'ACCEPTED', 'PRINTING']).count()
    completed_orders = Order.objects.filter(customer=user, status='COMPLETED').count()
    
    # Notifications
    notifications = user.notifications.all()[:15]
    unread_count = user.notifications.filter(is_read=False).count()
    
    context = {
        'orders': orders,
        'total_orders': total_orders,
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'user_shops': user_shops,
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'core/my_dashboard.html', context)


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    notif = Notification.objects.filter(id=notification_id, user=request.user).first()
    if notif:
        notif.is_read = True
        notif.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok', 'unread_count': request.user.notifications.filter(is_read=False).count()})
    return redirect('core:my_dashboard')


@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'unread_count': 0})
    return redirect('core:my_dashboard')
