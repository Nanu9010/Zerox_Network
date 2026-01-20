from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import HttpResponse
from .models import Shop
from orders.models import Order
from django.db.models import Sum


def register_shop(request):
    """Shop registration form - Step 0"""
    if request.method == 'POST':
        # Get form data
        shop_name = request.POST.get('shop_name')
        location = request.POST.get('location')
        phone = request.POST.get('phone')
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Price list
        a4_bw = request.POST.get('a4_bw_price')
        a4_color = request.POST.get('a4_color_price')
        a3_bw = request.POST.get('a3_bw_price')
        a3_color = request.POST.get('a3_color_price')
        
        # Create user account
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return render(request, 'shops/register.html')
        
        user = User.objects.create_user(username=username, password=password)
        
        # Create shop
        shop = Shop.objects.create(
            owner=user,
            name=shop_name,
            location=location,
            phone=phone,
            a4_bw_price=a4_bw,
            a4_color_price=a4_color,
            a3_bw_price=a3_bw,
            a3_color_price=a3_color,
            is_approved=False  # Requires admin approval
        )
        
        messages.success(request, f'Shop registered successfully! QR Code: {shop.qr_code}')
        messages.success(request, 'Your shop is now live and visible to customers!')
        
        # Auto-login
        login(request, user)
        return redirect('shops:dashboard')
    
    return render(request, 'shops/register.html')


def shop_list(request):
    """List all verified shops - Step 1"""
    shops = Shop.objects.filter(is_approved=True)
    search_query = request.GET.get('search', '')
    
    if search_query:
        shops = shops.filter(name__icontains=search_query) | shops.filter(location__icontains=search_query)
    
    return render(request, 'shops/list.html', {'shops': shops, 'search_query': search_query})


def shop_detail(request, shop_id):
    """Shop detail page - shows prices, allows file upload - Step 1 & 2"""
    shop = get_object_or_404(Shop, id=shop_id, is_approved=True)
    return render(request, 'shops/detail.html', {'shop': shop})


@login_required
def shop_dashboard(request):
    """Shop owner dashboard - Step 5"""
    try:
        shop = request.user.shop
    except:
        messages.error(request, 'You do not have a shop registered!')
        return redirect('shops:register')
    
    # Get all orders for this shop
    orders = shop.orders.all().order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        orders = orders.filter(status=status_filter)
    
    # Financial Calculations (Production Grade)
    completed_orders = shop.orders.filter(status='COMPLETED')
    
    total_gross = completed_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_commission = completed_orders.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
    total_earned = completed_orders.aggregate(Sum('shop_payout'))['shop_payout__sum'] or 0
    
    # Pending payout = Total earned - Paid total
    pending_payout = float(total_earned) - float(shop.paid_total)
    
    context = {
        'shop': shop,
        'orders': orders,
        'status_filter': status_filter,
        'financials': {
            'gross': total_gross,
            'commission': total_commission,
            'earned': total_earned,
            'pending': pending_payout,
            'paid': shop.paid_total
        }
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
    shop = get_object_or_404(Shop, qr_code=qr_code, is_approved=True)
    
    # Render the shop profile page (same as detail but accessible via QR code)
    return render(request, 'shops/profile.html', {'shop': shop})


def download_qr_png(request, shop_id):
    """Download QR code as PNG image"""
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
    try:
        shop = request.user.shop
    except:
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
    try:
        shop = request.user.shop
        image = get_object_or_404(ShopImage, id=image_id, shop=shop)
        image.delete()
        messages.success(request, 'Image deleted successfully.')
    except:
        messages.error(request, 'Error deleting image.')
    return redirect('shops:manage_images')


@login_required
def set_primary_image(request, image_id):
    """Set an image as the primary shop front"""
    try:
        shop = request.user.shop
        image = get_object_or_404(ShopImage, id=image_id, shop=shop)
        
        if not image.is_approved:
            messages.error(request, 'You can only set APPROVED images as primary.')
        else:
            image.is_primary = True
            image.save() # Model save() handles unsetting others
            messages.success(request, 'Primary image updated!')
    except:
        messages.error(request, 'Error updating primary image.')
    return redirect('shops:manage_images')
