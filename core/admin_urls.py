from django.urls import path
from . import admin_views
from . import staff_management

app_name = 'admin_portal'

urlpatterns = [
    # Dashboard
    path('dashboard/', admin_views.admin_dashboard, name='dashboard'),
    
    # Shop Management (UUID for shop_id)
    path('shops/', admin_views.shop_approvals, name='shop_approvals'),
    path('shops/approve/<uuid:shop_id>/', admin_views.approve_shop, name='approve_shop'),
    path('shops/reject/<uuid:shop_id>/', admin_views.reject_shop, name='reject_shop'),
    path('shops/suspend/<uuid:shop_id>/', admin_views.suspend_shop, name='suspend_shop'),
    path('shops/images/review/', admin_views.review_shop_images, name='review_images'),
    
    # User Management
    path('users/', admin_views.user_management, name='users'),
    path('users/<int:user_id>/', admin_views.view_user, name='view_user'),
    path('users/<int:user_id>/edit/', admin_views.edit_user, name='edit_user'),
    path('users/<int:user_id>/delete/', admin_views.delete_user, name='delete_user'),
    path('users/block/<int:user_id>/', admin_views.block_user, name='block_user'),
    path('users/unblock/<int:user_id>/', admin_views.unblock_user, name='unblock_user'),
    
    # Staff Management
    path('staff/add/', staff_management.add_staff, name='add_staff'),
    path('users/<int:user_id>/change-role/', staff_management.change_user_role, name='change_role'),
    
    # Dispute Resolution
    path('disputes/', admin_views.dispute_resolution, name='disputes'),
    path('disputes/resolve/<int:dispute_id>/', admin_views.resolve_dispute, name='resolve_dispute'),
    
    # Refund Processing
    path('refunds/', admin_views.refund_processing, name='refunds'),
    path('refunds/process/<int:refund_id>/', admin_views.process_refund, name='process_refund'),
    
    # Analytics
    path('analytics/', admin_views.analytics, name='analytics'),
]
