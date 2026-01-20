from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from shops.models import Shop, ShopImage

def is_admin(user):
    """Basic admin/staff access check"""
    return user.is_authenticated and (user.is_staff or (hasattr(user, 'profile') and user.profile.role in ['ADMIN', 'STAFF']))

def is_superadmin(user):
    """Restricted financial access check"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'ADMIN'

from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User
from core.models import UserProfile
from orders.models import Order, Dispute, Refund

@user_passes_test(is_admin)
def dashboard(request):
    """Admin Dashboard: Pending Shops, Images, and Analytics"""
    
    # 1. Analytics
    total_shops = Shop.objects.filter(is_approved=True).count()
    total_orders = Order.objects.filter(status='COMPLETED').count()
    
    # Calculate Platform Revenue (Commission from Shops)
    # Assuming 'earnings_total' on Shop is their net earnings? 
    # Or we calculate from Orders. Let's start simple: Sum of all order totals * standard commission (15%)
    # Ideally, we should have a Transaction model. For now, let's sum Order totals.
    total_sales = Order.objects.filter(status='COMPLETED').aggregate(Sum('total_price'))['total_price__sum'] or 0
    estimated_revenue = Order.objects.filter(status='COMPLETED').aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
    
    # 2. Pending Actions
    pending_shops = Shop.objects.filter(is_verified=False)
    pending_images = ShopImage.objects.filter(is_approved=False)
    
    # STAFF should not see revenue
    show_revenue = is_superadmin(request.user)
    
    return render(request, 'admin_portal/dashboard.html', {
        'stats': {
            'shops': total_shops,
            'orders': total_orders,
            'revenue': estimated_revenue if show_revenue else None,
            'active_shops': Shop.objects.filter(is_approved=True, is_suspended=False).count()
        },
        'show_revenue': show_revenue,
        'pending_shops': pending_shops,
        'pending_images': pending_images
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
            messages.success(request, f'Shop {shop.name} approved!')
        elif action == 'reject':
            shop.rejection_reason = request.POST.get('reason', 'Rejected by admin')
            shop.is_approved = False
            shop.save()
            messages.warning(request, f'Shop {shop.name} rejected.')
            
    return redirect('admin_portal:dashboard')

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
        
        user_obj.profile.role = request.POST.get('role')
        user_obj.profile.phone = request.POST.get('phone')
        user_obj.profile.is_blocked = request.POST.get('is_blocked') == 'true'
        
        new_pw = request.POST.get('new_password')
        if new_pw:
            user_obj.set_password(new_pw)
            
        user_obj.save()
        user_obj.profile.save()
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
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        role = request.POST.get('role', 'ADMIN')
        
        if password != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_staff = True
            user.first_name = full_name
            user.save()
            
            UserProfile.objects.create(user=user, role=role, phone=phone)
            messages.success(request, f'Staff member {username} created.')
            return redirect('admin_portal:users')
    return render(request, 'admin_portal/add_staff.html')

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
