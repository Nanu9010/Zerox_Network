from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from shops.models import Shop, ShopImage
from core.views import propagate_user_details

def is_admin(user):
    """Admin/staff access check — Shop Owners and Customers are blocked"""
    if not user.is_authenticated:
        return False
    if not hasattr(user, 'profile'):
        return False
    # Only STAFF and ADMIN roles allowed — never SHOP or CUSTOMER
    return user.is_staff and user.profile.role in ['ADMIN', 'STAFF']

def is_superadmin(user):
    """Restricted financial access check"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'ADMIN'

from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User
from core.models import UserProfile
from orders.models import Order, Dispute, Refund, AuditLog

@user_passes_test(is_admin)
def dashboard(request):
    """Admin Dashboard: Pending Shops, Images, Analytics, and Profile Overview"""
    
    # 1. Analytics & Overview
    total_shops = Shop.objects.filter(is_approved=True).count()
    total_orders = Order.objects.filter(status='COMPLETED').count()
    total_users = User.objects.count()
    pending_disputes = Dispute.objects.filter(status='OPEN').count()
    pending_refunds = Refund.objects.filter(status='PENDING').count()
    
    total_sales = Order.objects.filter(status='COMPLETED').aggregate(Sum('total_price'))['total_price__sum'] or 0
    estimated_revenue = Order.objects.filter(status='COMPLETED').aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
    
    # 2. Pending Actions
    pending_shops = Shop.objects.filter(is_verified=False)
    pending_images = ShopImage.objects.filter(is_approved=False)
    
    # 3. Recent Platform Log & Orders
    recent_activity = AuditLog.objects.select_related('user').all()[:8]
    recent_orders = Order.objects.select_related('shop').all()[:6]
    
    # STAFF should not see revenue
    show_revenue = is_superadmin(request.user)
    
    # Get user profile cleanly
    user_profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'role': 'ADMIN' if request.user.is_superuser else 'STAFF',
            'phone': ''
        }
    )
    
    return render(request, 'admin_portal/dashboard.html', {
        'stats': {
            'shops': total_shops,
            'orders': total_orders,
            'users': total_users,
            'pending_disputes': pending_disputes,
            'pending_refunds': pending_refunds,
            'revenue': estimated_revenue if show_revenue else None,
            'active_shops': Shop.objects.filter(is_approved=True, is_suspended=False).count()
        },
        'show_revenue': show_revenue,
        'pending_shops': pending_shops,
        'pending_images': pending_images,
        'recent_activity': recent_activity,
        'recent_orders': recent_orders,
        'user_profile': user_profile,
    })

@user_passes_test(is_admin)
def approve_shop(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            shop.is_verified = True
            shop.is_approved = True
            shop.save()
            messages.success(request, f'✅ Shop "{shop.name}" approved!')
        elif action == 'reject':
            shop.rejection_reason = request.POST.get('reason', 'Rejected by admin')
            shop.is_approved = False
            shop.is_verified = False
            shop.save()
            messages.warning(request, f'❌ Shop "{shop.name}" rejected.')
            
    return redirect('admin_portal:manage_shops')

@user_passes_test(is_admin)
def manage_shops(request):
    """List all shops with management actions"""
    query = request.GET.get('search', '')
    shops = Shop.objects.all().order_by('-created_at')
    
    if query:
        shops = shops.filter(name__icontains=query) | shops.filter(owner__email__icontains=query)
        
    return render(request, 'admin_portal/manage_shops.html', {'shops': shops, 'search_query': query})

@user_passes_test(is_admin)
def toggle_shop_status(request, shop_id):
    """Suspend or Activate a shop"""
    shop = get_object_or_404(Shop, id=shop_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'suspend':
            shop.is_suspended = True
            shop.suspension_reason = request.POST.get('reason', 'Admin Suspension')
            messages.warning(request, f'Shop {shop.name} suspended.')
        elif action == 'activate':
            shop.is_suspended = False
            shop.is_approved = True # Re-approve if needed
            messages.success(request, f'Shop {shop.name} activated.')
        shop.save()
    return redirect('admin_portal:manage_shops')

@user_passes_test(is_admin)
def approve_image(request, image_id):
    image = get_object_or_404(ShopImage, id=image_id)
    if request.method == 'POST':
        if 'approve' in request.POST:
            image.is_approved = True
            image.save()
            messages.success(request, 'Image approved.')
        elif 'delete' in request.POST:
            image.delete()
            messages.error(request, 'Image rejected and deleted.')
    return redirect('admin_portal:dashboard')

@user_passes_test(is_superadmin)
def transactions(request):
    """View all completed orders as financial transactions"""
    # Only completed orders have financial implication
    orders = Order.objects.filter(status='COMPLETED').order_by('-completed_at', '-updated_at')
    
    # Calculate totals
    total_volume = orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_commission = Order.objects.filter(status='COMPLETED').aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
    
    context = {
        'orders': orders,
        'total_volume': total_volume,
        'total_commission': total_commission
    }
    return render(request, 'admin_portal/transactions.html', context)

# --- NEW: User Management ---

@user_passes_test(is_admin)
def users_list(request):
    """List all users with search and filter"""
    query = request.GET.get('search', '')
    role = request.GET.get('role', '')
    
    users = User.objects.all().select_related('profile').order_by('-date_joined')
    
    if query:
        users = users.filter(
            Q(username__icontains=query) | 
            Q(email__icontains=query) | 
            Q(profile__phone__icontains=query)
        )
        
    if role and role != 'all':
        users = users.filter(profile__role=role)
        
    return render(request, 'admin_portal/users.html', {
        'users': users,
        'search_query': query,
        'selected_role': role
    })

@user_passes_test(is_admin)
def view_user(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    return render(request, 'admin_portal/view_user.html', {'view_user': user_obj})

@user_passes_test(is_admin)
def edit_user(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user_obj.username = request.POST.get('username')
        user_obj.email = request.POST.get('email')
        user_obj.first_name = request.POST.get('first_name', '')
        
        new_role = request.POST.get('role')
        user_obj.profile.role = new_role
        user_obj.profile.is_shop_owner = request.POST.get('is_shop_owner') == 'on'
        user_obj.profile.phone = request.POST.get('phone')
        user_obj.profile.is_blocked = request.POST.get('is_blocked') == 'true'
        
        # Sync is_staff with role
        if new_role in ['STAFF', 'ADMIN']:
            user_obj.is_staff = True
        else:
            user_obj.is_staff = False
        
        new_pw = request.POST.get('new_password')
        if new_pw:
            user_obj.set_password(new_pw)
            
        user_obj.save()
        user_obj.profile.save()
        
        # Propagate user details to Shop and Order records
        propagate_user_details(user_obj)
        
        messages.success(request, f'User {user_obj.username} updated.')
        return redirect('admin_portal:view_user', user_id=user_id)
    return render(request, 'admin_portal/edit_user.html', {'edit_user': user_obj})

@user_passes_test(is_admin)
def toggle_user_block(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    profile = user_obj.profile
    profile.is_blocked = not profile.is_blocked
    profile.save()
    status = "blocked" if profile.is_blocked else "unblocked"
    messages.warning(request, f'User {user_obj.username} {status}.')
    return redirect(request.META.get('HTTP_REFERER', 'admin_portal:users'))

@user_passes_test(is_superadmin) # Only superadmin can perform permanent blocks
def delete_user(request, user_id):
    """Note: We NO LONGER DELETE users to maintain audit integrity. 
    This view now performs a 'Permanent Block'."""
    user_obj = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        username = user_obj.username
        user_obj.profile.is_blocked = True
        user_obj.profile.save()
        messages.error(request, f'User {username} has been PERMANENTLY BLOCKED. Historical records are preserved.')
    return redirect('admin_portal:users')

@user_passes_test(is_admin)
def add_staff(request):
    """Redirect to add_user - add_staff is deprecated"""
    return redirect('admin_portal:add_user', role='STAFF')


@user_passes_test(is_admin)
def add_user(request):
    """Generic add user - handles all roles with optional shop creation"""
    role_filter = request.GET.get('role', 'STAFF')
    valid_roles = ['CUSTOMER', 'SHOP', 'STAFF', 'ADMIN']
    if role_filter not in valid_roles:
        role_filter = 'STAFF'

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        role = request.POST.get('role', role_filter)
        is_shop_owner = request.POST.get('is_shop_owner') == 'on'

        if role == 'BOTH':
            role = 'CUSTOMER'
            is_shop_owner = True
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

        create_shop = is_shop_owner and shop_name and shop_location and shop_phone

        errors = []
        if password != password2:
            errors.append('Passwords do not match.')
        if User.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        if email and User.objects.filter(email=email).exists():
            errors.append('Email already registered.')
        if role == 'SHOP' and not create_shop:
            errors.append('Shop name, location, and phone are required for Shop Owner accounts.')

        if errors:
            for e in errors:
                messages.error(request, e)
            context = {'role_filter': role_filter, 'form_data': request.POST}
            return render(request, 'admin_portal/add_user.html', context)

        user = User.objects.create_user(username=username, email=email, password=password)
        user.first_name = full_name
        if role in ['STAFF', 'ADMIN']:
            user.is_staff = True
        user.save()

        UserProfile.objects.create(user=user, role=role, is_shop_owner=is_shop_owner, phone=phone)

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
            messages.success(request, f'🏪 Shop "{shop_name}" created (QR: {shop.qr_code}). Pending approval.')

        role_label = dict(UserProfile.ROLE_CHOICES).get(role, role)
        messages.success(request, f'✅ {role_label} "{username}" created successfully!')
        return redirect('admin_portal:users')

    context = {'role_filter': role_filter}
    return render(request, 'admin_portal/add_user.html', context)

# --- NEW: Disputes & Refunds ---

@user_passes_test(is_admin)
def disputes_list(request):
    disputes = Dispute.objects.all().order_by('-created_at')
    return render(request, 'admin_portal/disputes.html', {'disputes': disputes})

@user_passes_test(is_admin)
def resolve_dispute(request, dispute_id):
    dispute = get_object_or_404(Dispute, id=dispute_id)
    if request.method == 'POST':
        decision = request.POST.get('decision')
        admin_notes = request.POST.get('admin_notes', '')
        refund_amount = request.POST.get('refund_amount')
        
        dispute.admin_decision = admin_notes
        dispute.resolved_at = timezone.now()
        
        if decision == 'recommend':
            # Staff Recommendation Logic
            dispute.status = 'IN_REVIEW' # Keep it open for Admin
            dispute.admin_decision = f"[STAFF RECOMMENDATION by {request.user.username}]: {admin_notes}\n\n---\n" + dispute.admin_decision
            dispute.save()
            messages.success(request, 'Recommendation saved. Dispute escalated to Admin.')
            return redirect('admin_portal:disputes')

        if decision in ['approve_full', 'approve_partial']:
            # SECURED: Only ADMIN can approve money decisions
            if not is_superadmin(request.user):
                messages.error(request, "Permission Denied: Only Admins can approve refunds. Staff can only leave recommendations.")
                return redirect('admin_portal:resolve_dispute', dispute_id=dispute.id)

            dispute.status = 'RESOLVED'
            dispute.refund_approved = True
            
            if decision == 'approve_full':
                dispute.refund_amount = dispute.order.total_price
                Refund.objects.create(
                    order=dispute.order,
                    amount=dispute.order.total_price,
                    reason='DISPUTE_APPROVED',
                    status='PENDING'
                )
                messages.success(request, f'Full refund of ₹{dispute.refund_amount} approved.')
            else:
                try:
                    amt = float(refund_amount)
                    dispute.refund_amount = amt
                    Refund.objects.create(
                        order=dispute.order,
                        amount=amt,
                        reason='DISPUTE_APPROVED',
                        status='PENDING'
                    )
                    messages.success(request, f'Partial refund of ₹{amt} approved.')
                except:
                    messages.error(request, 'Invalid refund amount.')
                    return redirect('admin_portal:resolve_dispute', dispute_id=dispute.id)
                
        else: # Reject
            dispute.status = 'REJECTED'
            dispute.refund_approved = False
            messages.warning(request, 'Refund request rejected.')
            
        dispute.save()
        return redirect('admin_portal:disputes')
        
    return render(request, 'admin_portal/resolve_dispute.html', {'dispute': dispute})

@user_passes_test(is_admin)
def refunds_list(request):
    refunds = Refund.objects.all().order_by('-created_at')
    return render(request, 'admin_portal/refunds.html', {'refunds': refunds})

@user_passes_test(is_admin)
def process_refund(request, refund_id):
    refund = get_object_or_404(Refund, id=refund_id)
    if request.method == 'POST':
        refund.status = 'COMPLETED'
        refund.processed_by = request.user
        from django.utils import timezone
        refund.processed_at = timezone.now()
        refund.save()
        messages.success(request, f'Refund for Order #{refund.order.id} marked as completed.')
    return redirect('admin_portal:refunds_list')

# --- NEW: Shop Approval Extensions ---

@user_passes_test(is_admin)
def shop_approvals(request):
    """List Shops with filtering for approvals"""
    status_filter = request.GET.get('status', 'pending')
    
    if status_filter == 'approved':
        shops = Shop.objects.filter(is_approved=True)
    elif status_filter == 'all':
        shops = Shop.objects.all()
    else: # Default pending
        shops = Shop.objects.filter(is_verified=False)
        
    return render(request, 'admin_portal/shop_approvals.html', {
        'shops': shops,
        'status_filter': status_filter
    })

@user_passes_test(is_admin)
def reject_shop_view(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id)
    if request.method == 'POST':
        shop.rejection_reason = request.POST.get('reason')
        shop.is_approved = False
        shop.is_verified = True # Mark as "processed"
        shop.save()
        messages.warning(request, f'Shop {shop.name} rejected.')
        return redirect('admin_portal:dashboard')
    return render(request, 'admin_portal/reject_shop.html', {'shop': shop})

@user_passes_test(is_admin)
def suspend_shop_view(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id)
    if request.method == 'POST':
        shop.is_suspended = True
        shop.suspension_reason = request.POST.get('reason')
        shop.save()
        messages.error(request, f'Shop {shop.name} suspended.')
        return redirect('admin_portal:manage_shops')
    return render(request, 'admin_portal/suspend_shop.html', {'shop': shop})

# --- NEW: Detailed Analytics & Image Review ---

@user_passes_test(is_superadmin)
def analytics_view(request):
    """Detailed analytics with time range filtering"""
    range_filter = request.GET.get('range', '30days')
    now = timezone.now()
    if range_filter == '7days':
        start_date = now - timedelta(days=7)
    else:
        start_date = now - timedelta(days=30)
        
    completed_orders = Order.objects.filter(status='COMPLETED', completed_at__gte=start_date)
    
    total_revenue = completed_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_commission = completed_orders.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
    shop_payouts = completed_orders.aggregate(Sum('shop_payout'))['shop_payout__sum'] or 0
    
    total_refunds = Refund.objects.filter(status='COMPLETED', processed_at__gte=start_date).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Order counts by status
    order_counts = Order.objects.filter(created_at__gte=start_date).values('status').annotate(count=Count('id'))
    
    # Top 5 shops
    top_shops = Shop.objects.filter(is_verified=True).annotate(
        order_count=Count('orders', filter=Q(orders__status='COMPLETED', orders__completed_at__gte=start_date))
    ).order_by('-order_count', '-rating')[:5]
    
    context = {
        'range_filter': range_filter,
        'total_revenue': total_revenue,
        'total_commission': total_commission,
        'shop_payouts': shop_payouts,
        'total_refunds': total_refunds,
        'order_counts': order_counts,
        'top_shops': top_shops
    }
    return render(request, 'admin_portal/analytics.html', context)

@user_passes_test(is_admin)
def review_images(request):
    """Dedicated bulk image review page"""
    if request.method == 'POST':
        image_id = request.POST.get('image_id')
        action = request.POST.get('action')
        image = get_object_or_404(ShopImage, id=image_id)
        
        if action == 'approve':
            image.is_approved = True
            image.save()
            messages.success(request, f'Image for {image.shop.name} approved.')
        elif action == 'reject':
            shop_name = image.shop.name
            image.delete()
            messages.warning(request, f'Image for {shop_name} deleted.')
            
    images = ShopImage.objects.filter(is_approved=False).select_related('shop').order_by('created_at')
    return render(request, 'admin_portal/review_images.html', {'images': images})

@user_passes_test(is_superadmin)
def payouts_list(request):
    """List all shops with payout status"""
    shops_qs = Shop.objects.filter(is_approved=True)
    shops_data = []
    
    total_revenue = 0
    total_paid = 0
    total_pending = 0
    
    for shop in shops_qs:
        # Calculate financials manually for now
        completed_orders = shop.orders.filter(status='COMPLETED')
        gross = completed_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
        net = completed_orders.aggregate(Sum('shop_payout'))['shop_payout__sum'] or 0
        paid = float(shop.paid_total)
        pending = float(net) - paid
        
        shops_data.append({
            'id': shop.id,
            'name': shop.name,
            'location': shop.location,
            'phone': shop.phone,
            'owner': shop.owner,
            'gross': gross,
            'net_earnings': net,
            'paid_total': paid,
            'pending_balance': pending
        })
        
        total_revenue += float(gross)
        total_paid += paid
        total_pending += max(0, pending)
        
    context = {
        'shops': shops_data,
        'summary': {
            'total_revenue': total_revenue,
            'total_paid': total_paid,
            'total_pending': total_pending
        }
    }
    return render(request, 'admin_portal/payouts.html', context)

@user_passes_test(is_superadmin)
def process_payout(request, shop_id):
    """Mark a pending balance as paid"""
    if request.method != 'POST':
        return redirect('admin_portal:payouts')
        
    shop = get_object_or_404(Shop, id=shop_id)
    try:
        amount = float(request.POST.get('amount', 0))
    except:
        messages.error(request, 'Invalid amount.')
        return redirect('admin_portal:payouts')
        
    if amount <= 0:
        messages.error(request, 'Amount must be positive.')
        return redirect('admin_portal:payouts')
        
    # Update shop total
    shop.paid_total = float(shop.paid_total) + amount
    shop.save()
    
    # Audit Log (Simple message for now)
    messages.success(request, f'Successfully recorded payout of ₹{amount} to {shop.name}.')
    return redirect('admin_portal:payouts')

@user_passes_test(is_superadmin)
def set_commission(request):
    """Set commission rate for a shop"""
    if request.method != 'POST':
        return redirect('admin_portal:manage_shops')
        
    shop_id = request.POST.get('shop_id')
    try:
        commission_rate = float(request.POST.get('commission_rate', 0))
    except:
        messages.error(request, 'Invalid commission rate.')
        return redirect('admin_portal:manage_shops')
        
    if commission_rate < 0 or commission_rate > 100:
        messages.error(request, 'Commission rate must be between 0 and 100.')
        return redirect('admin_portal:manage_shops')
        
    shop = get_object_or_404(Shop, id=shop_id)
    shop.commission_rate = commission_rate
    shop.save()
    
    messages.success(request, f'Commission rate for {shop.name} updated to {commission_rate}%.')
    return redirect('admin_portal:manage_shops')


# --- Payout Configuration & History ---

@user_passes_test(is_superadmin)
def payout_settings(request):
    """Configure payout schedule and settings"""
    from .models import PayoutConfig
    
    config = PayoutConfig.load()
    
    if request.method == 'POST':
        config.payout_enabled = request.POST.get('payout_enabled') == 'on'
        config.payout_hour = int(request.POST.get('payout_hour', 6))
        config.payout_minute = int(request.POST.get('payout_minute', 0))
        config.payout_mode = request.POST.get('payout_mode', 'IMPS')
        config.payout_days = request.POST.get('payout_days', '0,1,2,3,4,5,6')
        config.razorpayx_account_number = request.POST.get('razorpayx_account_number', '')
        config.save()
        
        messages.success(request, 'Payout settings updated successfully!')
        return redirect('admin_portal:payout_settings')
    
    return render(request, 'admin_portal/payout_settings.html', {'config': config})


@user_passes_test(is_superadmin)
def payout_history(request):
    """View all payout history"""
    from orders.models import Payout
    
    status_filter = request.GET.get('status', 'all')
    
    if status_filter == 'pending':
        payouts = Payout.objects.filter(status='PENDING')
    elif status_filter == 'processing':
        payouts = Payout.objects.filter(status='PROCESSING')
    elif status_filter == 'completed':
        payouts = Payout.objects.filter(status='COMPLETED')
    elif status_filter == 'failed':
        payouts = Payout.objects.filter(status='FAILED')
    else:
        payouts = Payout.objects.all()
    
    payouts = payouts.select_related('shop', 'shop__owner').order_by('-payout_date')
    
    # Calculate totals
    total_paid = Payout.objects.filter(status='COMPLETED').aggregate(Sum('amount'))['amount__sum'] or 0
    total_pending = Payout.objects.filter(status__in=['PENDING', 'PROCESSING']).aggregate(Sum('amount'))['amount__sum'] or 0
    total_failed = Payout.objects.filter(status='FAILED').aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'payouts': payouts,
        'status_filter': status_filter,
        'total_paid': total_paid,
        'total_pending': total_pending,
        'total_failed': total_failed,
    }
    return render(request, 'admin_portal/payout_history.html', context)


@user_passes_test(is_superadmin)
def retry_payout(request, payout_id):
    """Retry a failed payout"""
    from orders.models import Payout
    from shops.razorpay_payout import create_payout
    
    payout = get_object_or_404(Payout, id=payout_id, status='FAILED')
    
    if request.method == 'POST':
        shop = payout.shop
        bank_details = shop.bank_details
        
        if not bank_details or not bank_details.is_verified:
            messages.error(request, 'Shop does not have verified bank details.')
            return redirect('admin_portal:payout_history')
        
        # Process payout
        result = create_payout(
            bank_details=bank_details,
            amount=float(payout.amount),
            mode=payout.mode,
            reference_id=f"ZEROX-RETRY-{shop.id}-{payout.id}"
        )
        
        if result:
            payout.razorpay_payout_id = result['payout_id']
            payout.status = 'PROCESSING'
            payout.failure_reason = ''
            payout.processed_at = timezone.now()
            payout.save()
            
            messages.success(request, f'Retry payout initiated: {result["payout_id"]}')
        else:
            payout.failure_reason = 'Retry failed - Razorpay API error'
            payout.save()
            messages.error(request, 'Retry payout failed.')
    
    return redirect('admin_portal:payout_history')


@user_passes_test(is_superadmin)
def verify_bank_details(request, shop_id):
    """Admin verify shop bank details"""
    shop = get_object_or_404(Shop, id=shop_id)
    
    if request.method == 'POST':
        bank_details = getattr(shop, 'bank_details', None)
        if bank_details:
            bank_details.is_verified = True
            bank_details.verification_notes = request.POST.get('notes', '')
            bank_details.save()
            
            AuditLog.objects.create(
                user=request.user,
                action='BANK_DETAILS_VERIFIED',
                model_name='BankDetails',
                object_id=str(bank_details.id),
                details=f'Bank details verified for shop {shop.name}'
            )
            
            messages.success(request, f'Bank details for {shop.name} verified!')
        else:
            messages.error(request, 'No bank details found for this shop.')
    
    return redirect('admin_portal:manage_shops')


@user_passes_test(is_superadmin)
def edit_shop_location(request, shop_id):
    """Admin edit shop location with interactive map"""
    shop = get_object_or_404(Shop, id=shop_id)
    
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
                
                AuditLog.objects.create(
                    user=request.user,
                    action='SHOP_LOCATION_UPDATED',
                    model_name='Shop',
                    object_id=str(shop.id),
                    details=f'Shop location updated: {shop.name} -> Lat: {shop.latitude}, Lon: {shop.longitude}'
                )
                
                messages.success(request, f'Location updated for {shop.name}!')
            except ValueError:
                messages.error(request, 'Invalid coordinates.')
        else:
            messages.error(request, 'Please provide valid coordinates.')
        
        return redirect('admin_portal:manage_shops')
    
    return render(request, 'admin_portal/edit_shop_location.html', {'shop': shop})
