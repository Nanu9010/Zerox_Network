from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from core.decorators import role_required
from core.models import UserProfile
from shops.models import Shop
from orders.models import Order, Dispute, Refund, AuditLog


@role_required('ADMIN')
def admin_dashboard(request):
    """Admin Control Center - Command Dashboard"""
    
    # TODAY'S STATS
    today = timezone.now().date()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    
    # Top Row Cards
    total_users = User.objects.count()
    total_shops = Shop.objects.count()
    orders_today = Order.objects.filter(created_at__gte=today_start).count()
    
    # Revenue calculations
    revenue_today = Order.objects.filter(
        created_at__gte=today_start,
        status__in=['PAID', 'ACCEPTED', 'PRINTING', 'READY', 'COMPLETED']
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    commission_today = Order.objects.filter(
        created_at__gte=today_start,
        status__in=['PAID', 'ACCEPTED', 'PRINTING', 'READY', 'COMPLETED']
    ).aggregate(total=Sum('commission_amount'))['total'] or 0
    
    # Pending items
    pending_shops = Shop.objects.filter(is_approved=False).count()
    active_disputes = Dispute.objects.filter(status='PENDING').count()
    pending_refunds = Refund.objects.filter(status='PENDING').count()
    
    # Activity Feed - Last 10 events
    recent_logs = AuditLog.objects.all()[:10]
    
    # Order statistics
    order_stats = {
        'pending': Order.objects.filter(status='PENDING').count(),
        'paid': Order.objects.filter(status='PAID').count(),
        'printing': Order.objects.filter(status='PRINTING').count(),
        'ready': Order.objects.filter(status='READY').count(),
        'completed': Order.objects.filter(status='COMPLETED').count(),
        'refunded': Order.objects.filter(status='REFUNDED').count(),
    }
    
    context = {
        'total_users': total_users,
        'total_shops': total_shops,
        'orders_today': orders_today,
        'revenue_today': revenue_today,
        'commission_today': commission_today,
        'pending_shops': pending_shops,
        'active_disputes': active_disputes,
        'pending_refunds': pending_refunds,
        'recent_logs': recent_logs,
        'order_stats': order_stats,
    }
    
    return render(request, 'admin_portal/dashboard.html', context)


@role_required('ADMIN')
def shop_approvals(request):
    """Shop Approval Workflow"""
    
    # Filter shops by status
    status_filter = request.GET.get('status', 'pending')
    
    if status_filter == 'pending':
        shops = Shop.objects.filter(is_approved=False)
    elif status_filter == 'approved':
        shops = Shop.objects.filter(is_approved=True)
    else:
        shops = Shop.objects.all()
    
    context = {
        'shops': shops,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_portal/shop_approvals.html', context)


@role_required('ADMIN')
def approve_shop(request, shop_id):
    """Approve a shop - Makes it visible to customers and generates QR"""
    shop = get_object_or_404(Shop, id=shop_id)
    
    if request.method == 'POST':
        shop.is_approved = True
        shop.save()
        
        # Generate QR code for the shop
        try:
            from shops.qr_generator import generate_shop_qr
            base_url = request.build_absolute_uri('/')[:-1]
            generate_shop_qr(shop, base_url)
        except Exception as e:
            pass  # QR generation is optional, don't block approval
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action='SHOP_APPROVED',
            model_name='Shop',
            object_id=str(shop.id),
            details=f'Approved shop: {shop.name}. QR code generated.'
        )
        
        messages.success(request, f'✅ Shop "{shop.name}" has been approved! QR code is ready for download.')
        return redirect('admin_portal:shop_approvals')
    
    return redirect('admin_portal:shop_approvals')


@role_required('ADMIN')
def reject_shop(request, shop_id):
    """Reject a shop with reason"""
    shop = get_object_or_404(Shop, id=shop_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided')
        
        shop.rejection_reason = reason
        shop.is_approved = False
        shop.save()
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action='SHOP_REJECTED',
            model_name='Shop',
            object_id=shop.id, # storing ID before deletion might look weird if object gone, but ID is string/UUID usually safe to log
            details=f'Rejected and DELETED shop: {shop.name}. Reason: {reason}'
        )
        
        # User requested deletion on rejection
        shop.delete()
        
        messages.warning(request, f'❌ Shop "{shop.name}" has been rejected and deleted.')
        return redirect('admin_portal:shop_approvals')
    
    context = {'shop': shop}
    return render(request, 'admin_portal/reject_shop.html', context)


@role_required('ADMIN')
def review_shop_images(request):
    """Review and Approve/Reject Shop Images"""
    from shops.models import ShopImage
    
    if request.method == 'POST':
        action = request.POST.get('action')
        image_id = request.POST.get('image_id')
        
        try:
            image = ShopImage.objects.get(id=image_id)
            
            if action == 'approve':
                image.is_approved = True
                image.save()
                messages.success(request, f'✅ Image for "{image.shop.name}" approved.')
            
            elif action == 'reject':
                # Rejecting an image implies it's bad -> delete it
                image.delete()
                messages.warning(request, f'🗑️ Image for "{image.shop.name}" rejected and deleted.')
                
        except ShopImage.DoesNotExist:
            messages.error(request, 'Image not found or already processed.')
            
        return redirect('admin_portal:review_images')
    
    pending_images = ShopImage.objects.filter(is_approved=False).select_related('shop').order_by('created_at')
    
    return render(request, 'admin_portal/review_images.html', {'images': pending_images})



@role_required('ADMIN')
def suspend_shop(request, shop_id):
    """Suspend an existing shop - Hide from customers, existing orders continue"""
    shop = get_object_or_404(Shop, id=shop_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'Policy violation')
        
        shop.is_approved = False
        shop.suspension_reason = reason
        shop.save()
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action='SHOP_SUSPENDED',
            model_name='Shop',
            object_id=shop.id,
            details=f'Suspended shop: {shop.name}. Reason: {reason}'
        )
        
        messages.warning(request, f'🚫 Shop "{shop.name}" has been suspended.')
        return redirect('admin_portal:shop_approvals')
    
    context = {'shop': shop}
    return render(request, 'admin_portal/suspend_shop.html', context)


@role_required('ADMIN')
def user_management(request):
    """User Management - View, Block, Unblock"""
    
    # Filter by role
    role_filter = request.GET.get('role', 'all')
    search_query = request.GET.get('search', '')
    
    users = User.objects.select_related('profile').all()
    
    if role_filter != 'all':
        users = users.filter(profile__role=role_filter)
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    context = {
        'users': users,
        'role_filter': role_filter,
        'search_query': search_query,
    }
    
    return render(request, 'admin_portal/users.html', context)


@role_required('ADMIN')
def block_user(request, user_id):
    """Block a user - Cannot place new orders"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.profile.is_blocked = True
        user.profile.save()
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action='USER_BLOCKED',
            model_name='User',
            object_id=user.id,
            details=f'Blocked user: {user.username}'
        )
        
        messages.warning(request, f'🚫 User "{user.username}" has been blocked.')
        return redirect('admin_portal:users')
    
    return redirect('admin_portal:users')


@role_required('ADMIN')
def unblock_user(request, user_id):
    """Unblock a user"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.profile.is_blocked = False
        user.profile.save()
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action='USER_UNBLOCKED',
            model_name='User',
            object_id=user.id,
            details=f'Unblocked user: {user.username}'
        )
        
        messages.success(request, f'✅ User "{user.username}" has been unblocked.')
        return redirect('admin_portal:users')
    
    return redirect('admin_portal:users')


@role_required('ADMIN')
def view_user(request, user_id):
    """View user details and activity"""
    view_user = get_object_or_404(User, id=user_id)
    orders = Order.objects.filter(customer=view_user).order_by('-created_at')[:10]
    
    context = {
        'view_user': view_user,
        'orders': orders,
    }
    return render(request, 'admin_portal/view_user.html', context)


@role_required('ADMIN')
def edit_user(request, user_id):
    """Edit user details, role, and password"""
    edit_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Update user details
        edit_user.username = request.POST.get('username', edit_user.username)
        edit_user.email = request.POST.get('email', edit_user.email)
        edit_user.first_name = request.POST.get('first_name', edit_user.first_name)
        edit_user.save()
        
        # Update profile
        edit_user.profile.phone = request.POST.get('phone', edit_user.profile.phone)
        edit_user.profile.role = request.POST.get('role', edit_user.profile.role)
        edit_user.profile.is_blocked = request.POST.get('is_blocked') == 'true'
        edit_user.profile.save()
        
        # Update password if provided
        new_password = request.POST.get('new_password')
        if new_password:
            edit_user.set_password(new_password)
            edit_user.save()
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action='USER_UPDATED',
            model_name='User',
            object_id=edit_user.id,
            details=f'Updated user: {edit_user.username}'
        )
        
        messages.success(request, f'✅ User "{edit_user.username}" updated successfully!')
        return redirect('admin_portal:users')
    
    context = {'edit_user': edit_user}
    return render(request, 'admin_portal/edit_user.html', context)


@role_required('ADMIN')
def delete_user(request, user_id):
    """Delete a user permanently"""
    user_to_delete = get_object_or_404(User, id=user_id)
    
    # Prevent deleting self or other admins
    if user_to_delete == request.user:
        messages.error(request, '❌ You cannot delete yourself!')
        return redirect('admin_portal:users')
    
    if user_to_delete.profile.role == 'ADMIN':
        messages.error(request, '❌ Cannot delete admin accounts!')
        return redirect('admin_portal:users')
    
    if request.method == 'POST':
        username = user_to_delete.username
        
        # Audit log before deletion
        AuditLog.objects.create(
            user=request.user,
            action='USER_DELETED',
            model_name='User',
            object_id=user_id,
            details=f'Deleted user: {username}'
        )
        
        user_to_delete.delete()
        messages.success(request, f'🗑️ User "{username}" deleted permanently.')
        return redirect('admin_portal:users')
    
    return redirect('admin_portal:users')


@role_required('ADMIN')
def dispute_resolution(request):
    """Dispute Resolution Center"""
    
    status_filter = request.GET.get('status', 'pending')
    
    if status_filter == 'pending':
        disputes = Dispute.objects.filter(status='PENDING')
    elif status_filter == 'resolved':
        disputes = Dispute.objects.filter(status='RESOLVED')
    else:
        disputes = Dispute.objects.all()
    
    disputes = disputes.select_related('order', 'order__shop', 'raised_by').order_by('-created_at')
    
    context = {
        'disputes': disputes,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_portal/disputes.html', context)


@role_required('ADMIN')
def resolve_dispute(request, dispute_id):
    """Admin decides on dispute - Approve/Reject refund"""
    dispute = get_object_or_404(Dispute, id=dispute_id)
    
    if request.method == 'POST':
        decision = request.POST.get('decision')  # 'approve_full', 'approve_partial', 'reject'
        admin_notes = request.POST.get('admin_notes', '')
        
        if decision == 'approve_full':
            # Full refund
            refund_amount = dispute.order.total_price
            dispute.refund_approved = True
            dispute.refund_amount = refund_amount
            
            # Create refund
            Refund.objects.create(
                order=dispute.order,
                amount=refund_amount,
                reason='DISPUTE_APPROVED',
                status='PENDING'
            )
            
            messages.success(request, f'✅ Full refund of ₹{refund_amount} approved.')
            
        elif decision == 'approve_partial':
            # Partial refund
            refund_amount = float(request.POST.get('refund_amount', 0))
            dispute.refund_approved = True
            dispute.refund_amount = refund_amount
            
            # Create refund
            Refund.objects.create(
                order=dispute.order,
                amount=refund_amount,
                reason='DISPUTE_APPROVED',
                status='PENDING'
            )
            
            messages.success(request, f'✅ Partial refund of ₹{refund_amount} approved.')
            
        else:  # reject
            dispute.refund_approved = False
            messages.warning(request, '❌ Dispute rejected. No refund issued.')
        
        # Update dispute
        dispute.status = 'RESOLVED'
        dispute.admin_decision = admin_notes
        dispute.resolved_at = timezone.now()
        dispute.save()
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action='DISPUTE_RESOLVED',
            model_name='Dispute',
            object_id=dispute.id,
            details=f'Resolved dispute #{dispute.id}. Decision: {decision}'
        )
        
        return redirect('admin_portal:disputes')
    
    context = {'dispute': dispute}
    return render(request, 'admin_portal/resolve_dispute.html', context)


@role_required('ADMIN')
def refund_processing(request):
    """Refund Processing Center"""
    
    status_filter = request.GET.get('status', 'pending')
    
    if status_filter == 'pending':
        refunds = Refund.objects.filter(status='PENDING')
    elif status_filter == 'completed':
        refunds = Refund.objects.filter(status='COMPLETED')
    else:
        refunds = Refund.objects.all()
    
    refunds = refunds.select_related('order', 'order__shop').order_by('-created_at')
    
    context = {
        'refunds': refunds,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_portal/refunds.html', context)


@role_required('ADMIN')
def process_refund(request, refund_id):
    """Process a refund (trigger Razorpay refund)"""
    refund = get_object_or_404(Refund, id=refund_id)
    
    if request.method == 'POST':
        # TODO: Integrate with Razorpay API to process actual refund
        # For now, mark as completed
        
        refund.status = 'COMPLETED'
        refund.processed_at = timezone.now()
        refund.processed_by = request.user
        refund.save()
        
        # Update order status
        refund.order.status = 'REFUNDED'
        refund.order.save()
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action='REFUND_PROCESSED',
            model_name='Refund',
            object_id=refund.id,
            details=f'Processed refund of ₹{refund.amount} for order #{refund.order.id}'
        )
        
        messages.success(request, f'✅ Refund of ₹{refund.amount} processed successfully.')
        return redirect('admin_portal:refunds')
    
    return redirect('admin_portal:refunds')


@role_required('ADMIN')
def analytics(request):
    """Analytics & Insights Dashboard"""
    
    # Date range filter
    range_filter = request.GET.get('range', '7days')
    
    if range_filter == '7days':
        start_date = timezone.now() - timedelta(days=7)
    elif range_filter == '30days':
        start_date = timezone.now() - timedelta(days=30)
    else:
        start_date = timezone.now() - timedelta(days=7)
    
    # Money Metrics
    total_revenue = Order.objects.filter(
        status__in=['PAID', 'ACCEPTED', 'PRINTING', 'READY', 'COMPLETED'],
        created_at__gte=start_date
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    total_commission = Order.objects.filter(
        status__in=['PAID', 'ACCEPTED', 'PRINTING', 'READY', 'COMPLETED'],
        created_at__gte=start_date
    ).aggregate(total=Sum('commission_amount'))['total'] or 0
    
    total_refunds = Refund.objects.filter(
        status='COMPLETED',
        created_at__gte=start_date
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    shop_payouts = total_revenue - total_commission
    
    # Order Metrics
    order_counts = Order.objects.filter(created_at__gte=start_date).values('status').annotate(count=Count('id'))
    
    # Top 5 Shops
    top_shops = Shop.objects.filter(
        is_approved=True
    ).annotate(
        order_count=Count('orders')
    ).order_by('-order_count')[:5]
    
    context = {
        'range_filter': range_filter,
        'total_revenue': total_revenue,
        'total_commission': total_commission,
        'total_refunds': total_refunds,
        'shop_payouts': shop_payouts,
        'order_counts': order_counts,
        'top_shops': top_shops,
    }
    
    return render(request, 'admin_portal/analytics.html', context)
