from django.urls import path
from . import views

app_name = 'admin_portal'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('approve-shop/<uuid:shop_id>/', views.approve_shop, name='approve_shop'),
    path('approve-image/<int:image_id>/', views.approve_image, name='approve_image'),
    
    # Shop Management
    path('shops/', views.manage_shops, name='manage_shops'),
    path('shops/<uuid:shop_id>/toggle/', views.toggle_shop_status, name='toggle_shop_status'),
    
    # Shop Approvals (Extended)
    path('approvals/', views.shop_approvals, name='shop_approvals'),
    path('reject-shop/<uuid:shop_id>/', views.reject_shop_view, name='reject_shop'),
    path('suspend-shop/<uuid:shop_id>/', views.suspend_shop_view, name='suspend_shop'),
    
    # User Management
    path('users/', views.users_list, name='users'),
    path('users/add-staff/', views.add_staff, name='add_staff'),
    path('users/<int:user_id>/', views.view_user, name='view_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('users/<int:user_id>/block/', views.toggle_user_block, name='block_user'),
    path('users/<int:user_id>/unblock/', views.toggle_user_block, name='unblock_user'),
    
    # Financials & Orders
    path('transactions/', views.transactions, name='transactions'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('disputes/', views.disputes_list, name='disputes'),
    path('disputes/<int:dispute_id>/resolve/', views.resolve_dispute, name='resolve_dispute'),
    path('refunds/', views.refunds_list, name='refunds_list'),
    path('refunds/<int:refund_id>/process/', views.process_refund, name='process_refund'),
    path('payouts/', views.payouts_list, name='payouts'),
    path('payouts/<uuid:shop_id>/process/', views.process_payout, name='process_payout'),
    
    # Media Moderation
    path('images/review/', views.review_images, name='review_images'),
    
    # Commission Management
    path('set-commission/', views.set_commission, name='set_commission'),
]
