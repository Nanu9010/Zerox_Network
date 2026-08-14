from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import HttpResponse
from .models import Shop, ShopImage
from .forms import ShopImageForm
from orders.models import Order
from django.db.models import Sum


def register_shop(request):
    """Shop registration form - supports multiple shops per user"""
    # Check if user is already logged in
    if request.user.is_authenticated:
        user = request.user
    else:
        user = None
    
    if request.method == 'POST':
        # Get form data
        shop_name = request.POST.get('shop_name')
        location = request.POST.get('location')
        phone = request.POST.get('phone')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # Price list
        a4_bw = request.POST.get('a4_bw_price')
        a4_color = request.POST.get('a4_color_price')
        a3_bw = request.POST.get('a3_bw_price')
        a3_color = request.POST.get('a3_color_price')
        
        # Create user account if not logged in
        if not user:
            username = request.POST.get('username')
            password = request.POST.get('password')
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists!')
                return render(request, 'shops/register.html')
            
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
        
        # Create shop
        shop = Shop.objects.create(
            owner=user,
            name=shop_name,
            location=location,
            phone=phone,
            latitude=latitude if latitude else None,
            longitude=longitude if longitude else None,
            a4_bw_price=a4_bw,
            a4_color_price=a4_color,
            a3_bw_price=a3_bw,
            a3_color_price=a3_color,
            is_approved=False  # Requires admin approval
        )
        
        messages.success(request, f'Shop "{shop_name}" registered successfully! QR Code: {shop.qr_code}')
        messages.success(request, 'Your shop is now live and visible to customers!')
        
        return redirect('shops:dashboard')
    
    return render(request, 'shops/register.html')


def shop_list(request):
    """List all verified shops with optional geolocation sorting"""
    shops = Shop.objects.filter(is_approved=True, is_suspended=False)
    search_query = request.GET.get('search', '')
    user_lat = request.GET.get('lat')
    user_lon = request.GET.get('lon')
    max_distance = request.GET.get('distance', '')  # max distance filter in km
    
    # Text search
    if search_query:
        shops = shops.filter(name__icontains=search_query) | shops.filter(location__icontains=search_query)
    
    # Distance filtering and sorting
    shop_data = []
    for shop in shops:
        distance = None
        if user_lat and user_lon and shop.latitude and shop.longitude:
            distance = shop.distance_from(float(user_lat), float(user_lon))
        
        # Filter by max distance if provided
        if max_distance and distance is not None:
            if distance > float(max_distance):
                continue
        
        shop_data.append({
            'shop': shop,
            'distance': distance
        })
    
    # Sort by distance (shops with distance first, then shops without)
    if user_lat and user_lon:
        shop_data.sort(key=lambda x: (x['distance'] is None, x['distance'] or 0))
    
    return render(request, 'shops/list.html', {
        'shop_data': shop_data,
        'shops': shops,
        'search_query': search_query,
        'user_lat': user_lat or '',
        'user_lon': user_lon or '',
        'max_distance': max_distance
    })


def shop_detail(request, shop_id):
    """Shop detail page - shows prices, allows file upload - Step 1 & 2"""
    shop = get_object_or_404(Shop, id=shop_id)
    if not shop.is_approved:
        if request.user.is_authenticated and (request.user == shop.owner or request.user.is_staff):
            messages.info(request, "Preview mode: Your shop is currently pending admin approval.")
        else:
            messages.warning(request, "This shop is currently pending approval by an administrator.")
            return redirect('shops:list')
    return render(request, 'shops/detail.html', {'shop': shop})


@login_required
def shop_dashboard(request):
    """Shop owner dashboard - shows all shops or single shop"""
    from django.db.models import Q
    # Get all shops owned by this user
    shops = request.user.shops.all()
    
    if not shops.exists():
        # Smart fallback: Auto-link shop if user email or username matches shop name or phone
        user_phone = getattr(getattr(request.user, 'profile', None), 'phone', '')
        user_email = request.user.email
        user_name = request.user.username
        
        fallback_query = Q()
        if user_email:
            fallback_query |= Q(name__icontains=user_email.split('@')[0])
        if user_name:
            fallback_query |= Q(name__icontains=user_name)
        if user_phone:
            fallback_query |= Q(phone=user_phone)
            
        if fallback_query:
            candidate_shops = Shop.objects.filter(fallback_query)
            if candidate_shops.exists():
                candidate_shops.update(owner=request.user)
                shops = request.user.shops.all()

    if not shops.exists():
        messages.info(request, 'Welcome Partner! Please register your shop details below to activate your partner dashboard.')
        return redirect('shops:register')
    
    # Check if specific shop is selected
    shop_id = request.GET.get('shop')
    if shop_id:
        selected_shop = get_object_or_404(Shop, id=shop_id, owner=request.user)
    else:
        selected_shop = shops.first()
    
    # Handle image upload from dashboard
    if request.method == 'POST' and 'upload_image' in request.POST:
        form = ShopImageForm(request.POST, request.FILES)
        if form.is_valid():
            shop_image = form.save(commit=False)
            shop_image.shop = selected_shop
            shop_image.is_approved = False
            shop_image.save()
            messages.success(request, 'Image uploaded! It will be live after admin approval.')
            return redirect('shops:dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    # Get all orders for selected shop
    orders = selected_shop.orders.all().order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        orders = orders.filter(status=status_filter)
    
    # --- SEARCH orders by customer phone / name / order ID ---
    search_query = request.GET.get('q', '').strip()
    if search_query:
        from django.db.models import Q as DQ
        orders = orders.filter(
            DQ(customer_name__icontains=search_query) |
            DQ(customer_phone__icontains=search_query) |
            DQ(id__icontains=search_query)
        )
    
    # --- SORT orders ---
    sort_by = request.GET.get('sort', '-created_at')
    SORT_OPTIONS = {
        '-created_at': '-created_at',
        'created_at': 'created_at',
        '-total_price': '-total_price',
        'total_price': 'total_price',
        'status': 'status',
    }
    sort_field = SORT_OPTIONS.get(sort_by, '-created_at')
    orders = orders.order_by(sort_field)
    
    # --- VIEW MODE (list / grid) ---
    view_mode = request.GET.get('view', 'list')  # list or grid
    
    # Financial Calculations (Production Grade)
    completed_orders = selected_shop.orders.filter(status='COMPLETED')
    
    total_gross = completed_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_commission = completed_orders.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
    total_earned = completed_orders.aggregate(Sum('shop_payout'))['shop_payout__sum'] or 0
    
    # Pending payout = Total earned - Paid total
    pending_payout = float(total_earned) - float(selected_shop.paid_total)
    
    # Order Status Counters for Shop Owner Summary
    all_shop_orders = selected_shop.orders.all()
    order_counts = {
        'total': all_shop_orders.count(),
        'paid_pending': all_shop_orders.filter(status__in=['PAID', 'PENDING']).count(),
        'accepted_printing': all_shop_orders.filter(status__in=['ACCEPTED', 'PRINTING']).count(),
        'ready': all_shop_orders.filter(status='READY').count(),
        'completed': all_shop_orders.filter(status='COMPLETED').count(),
    }

    # Aggregate stats across all shops
    all_shops_stats = []
    for s in shops:
        s_completed = s.orders.filter(status='COMPLETED')
        s_gross = s_completed.aggregate(Sum('total_price'))['total_price__sum'] or 0
        s_earned = s_completed.aggregate(Sum('shop_payout'))['shop_payout__sum'] or 0
        s_pending = float(s_earned) - float(s.paid_total)
        all_shops_stats.append({
            'shop': s,
            'gross': s_gross,
            'earned': s_earned,
            'pending': s_pending,
            'is_selected': s.id == selected_shop.id
        })
    
    context = {
        'shop': selected_shop,
        'all_shops': all_shops_stats,
        'orders': orders,
        'order_counts': order_counts,
        'status_filter': status_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'view_mode': view_mode,
        'sort_options': [
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('-total_price', 'Price: High → Low'),
            ('total_price', 'Price: Low → High'),
            ('status', 'Status A–Z'),
        ],
        'financials': {
            'gross': total_gross,
            'commission': total_commission,
            'earned': total_earned,
            'pending': pending_payout,
            'paid': selected_shop.paid_total
        },
        'shop_images': selected_shop.images.all().order_by('-is_primary', '-created_at')[:6],
        'shop_image_form': ShopImageForm(),
    }
    
    return render(request, 'shops/dashboard.html', context)


@login_required
def accept_order(request, order_id):
    """Shop accepts order - Step 5"""
    order = get_object_or_404(Order, id=order_id)
    
    # Verify shop ownership
    if order.shop.owner != request.user:
        messages.error(request, 'Unauthorized action!')
        return redirect('shops:dashboard')
    
    order.status = 'PRINTING'
    order.save()
    
    messages.success(request, f'Order #{order.id} accepted! Please download files and start printing.')
    return redirect('shops:dashboard')


@login_required
def reject_order(request, order_id):
    """Shop rejects order - Step 5"""
    order = get_object_or_404(Order, id=order_id)
    
    if order.shop.owner != request.user:
        messages.error(request, 'Unauthorized action!')
        return redirect('shops:dashboard')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided')
        order.status = 'REJECTED'
        order.rejection_reason = reason
        order.save()
        
        messages.warning(request, f'Order #{order.id} rejected. Refund will be processed.')
        return redirect('shops:dashboard')
    
    return render(request, 'shops/reject_order.html', {'order': order})


@login_required
def mark_ready(request, order_id):
    """Mark order as ready for pickup & generate PIN - Step 6"""
    order = get_object_or_404(Order, id=order_id)
    
    if order.shop.owner != request.user:
        messages.error(request, 'Unauthorized action!')
        return redirect('shops:dashboard')
    
    # Directly mark as ready and generate PIN (no proof required)
    order.status = 'READY'
    order.generate_pin()
    messages.success(request, f'Order #{order.id} is ready for pickup! PIN: {order.pin_code}')
    return redirect('shops:dashboard')


@login_required
def complete_order(request, order_id):
    """Complete order after PIN verification - Step 7"""
    order = get_object_or_404(Order, id=order_id)
    
    if order.shop.owner != request.user:
        messages.error(request, 'Unauthorized action!')
        return redirect('shops:dashboard')
    
    if request.method == 'POST':
        entered_pin = request.POST.get('pin')
        
        if entered_pin == order.pin_code:
            order.status = 'COMPLETED'
            order.save()
            messages.success(request, f'Order #{order.id} completed successfully!')
        else:
            messages.error(request, 'Invalid PIN!')
    
    return redirect('shops:dashboard')


# ==========================================
# QR CODE & SHOP PROFILE VIEWS
# ==========================================

def shop_profile_by_qr(request, qr_code):
    """Shop profile page accessed via QR code scan
    This is the destination URL when customers scan the QR code
    """
    # Find shop by QR code
    shop = get_object_or_404(Shop, qr_code=qr_code)
    
    if not shop.is_approved:
        if request.user.is_authenticated and (request.user == shop.owner or request.user.is_staff):
            messages.info(request, "Preview mode: Your shop is currently pending admin approval.")
        else:
            messages.warning(request, "This shop is currently pending approval by an administrator.")
            return redirect('core:home')
            
    # Render the shop profile page (same as detail but accessible via QR code)
    return render(request, 'shops/profile.html', {'shop': shop})


def download_qr_png(request, shop_id):
    """Download shop QR code as PNG image file"""
    shop = get_object_or_404(Shop, id=shop_id)
    
    # Import here to avoid circular imports
    from .qr_generator import get_qr_image_bytes
    
    base_url = request.build_absolute_uri('/')[:-1]  # Get base URL
    qr_buffer = get_qr_image_bytes(shop, base_url)
    
    response = HttpResponse(qr_buffer.getvalue(), content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="{shop.qr_code}_QR.png"'
    
    return response


def download_qr_poster(request, shop_id):
    """Download QR code poster as PDF"""
    shop = get_object_or_404(Shop, id=shop_id)
    
    # Import here to avoid circular imports
    from .poster_generator import generate_shop_poster
    
    base_url = request.build_absolute_uri('/')[:-1]  # Get base URL
    poster_buffer = generate_shop_poster(shop, base_url)
    
    response = HttpResponse(poster_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{shop.qr_code}_Poster.pdf"'
    
    return response


from .forms import ShopImageForm
from .models import ShopImage

@login_required
def manage_shop_images(request):
    """Manage shop images - Step 8 (Identity)"""
    shop = request.user.shops.first()
    if not shop:
        messages.error(request, 'You do not have a shop registered!')
        return redirect('shops:register')

    if request.method == 'POST':
        form = ShopImageForm(request.POST, request.FILES)
        if form.is_valid():
            shop_image = form.save(commit=False)
            shop_image.shop = shop
            # Admin approval required as per rules
            shop_image.is_approved = False 
            shop_image.save()
            messages.success(request, 'Image uploaded! It will be live after admin approval.')
            return redirect('shops:manage_images')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ShopImageForm()

    images = shop.images.all().order_by('-is_primary', '-created_at')
    return render(request, 'shops/manage_images.html', {'shop': shop, 'images': images, 'form': form})


@login_required
def delete_image(request, image_id):
    """Delete a shop image"""
    shop = request.user.shops.first()
    if not shop:
        messages.error(request, 'Error: No shop found.')
        return redirect('shops:register')
    image = get_object_or_404(ShopImage, id=image_id, shop=shop)
    image.delete()
    messages.success(request, 'Image deleted successfully.')
    return redirect('shops:manage_images')


@login_required
def set_primary_image(request, image_id):
    """Set an image as the primary shop front"""
    shop = request.user.shops.first()
    if not shop:
        messages.error(request, 'Error: No shop found.')
        return redirect('shops:register')
    image = get_object_or_404(ShopImage, id=image_id, shop=shop)
    if not image.is_approved:
        messages.error(request, 'You can only set APPROVED images as primary.')
    else:
        image.is_primary = True
        image.save()  # Model save() handles unsetting others
        messages.success(request, 'Primary image updated!')
    return redirect('shops:manage_images')


@login_required
def update_shop_location(request, shop_id):
    """Shop owner update their shop location with interactive map"""
    shop = get_object_or_404(Shop, id=shop_id, owner=request.user)
    
    if request.method == 'POST':
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        location = request.POST.get('location', shop.location)
        
        if latitude and longitude:
            try:
                shop.latitude = float(latitude)
                shop.longitude = float(longitude)
                shop.location = location
                shop.save()
                
                messages.success(request, 'Shop location updated successfully!')
            except ValueError:
                messages.error(request, 'Invalid coordinates.')
        else:
            messages.error(request, 'Please provide valid coordinates.')
        
        return redirect('shops:dashboard')
    
    return render(request, 'shops/update_location.html', {'shop': shop})
