from django.urls import path
from . import views
from . import settings_views
from . import bank_views
from . import api_views

app_name = 'shops'

urlpatterns = [
    path('register/', views.register_shop, name='register'),
    path('dashboard/', views.shop_dashboard, name='dashboard'),
    path('list/', views.shop_list, name='list'),
    path('<uuid:shop_id>/', views.shop_detail, name='detail'),
    path('order/<int:order_id>/accept/', views.accept_order, name='accept_order'),
    path('order/<int:order_id>/reject/', views.reject_order, name='reject_order'),
    path('order/<int:order_id>/ready/', views.mark_ready, name='mark_ready'),
    path('order/<int:order_id>/complete/', views.complete_order, name='complete_order'),
    
    # QR Code Routes - Unique Shop Profiles
    path('<str:qr_code>/', views.shop_profile_by_qr, name='profile_by_qr'),
    path('qr/download/<uuid:shop_id>/png/', views.download_qr_png, name='download_qr_png'),
    path('qr/download/<uuid:shop_id>/poster/', views.download_qr_poster, name='download_qr_poster'),
    
    # Image Management (New)
    path('dashboard/images/', views.manage_shop_images, name='manage_images'),
    path('dashboard/images/delete/<int:image_id>/', views.delete_image, name='delete_image'),
    path('dashboard/images/primary/<int:image_id>/', views.set_primary_image, name='set_primary_image'),
    path('dashboard/settings/', settings_views.shop_settings, name='settings'),
    
    # Bank Details & Payouts
    path('dashboard/bank/', bank_views.bank_details, name='bank_details'),
    path('dashboard/payouts/', bank_views.payout_history, name='payout_history'),
    
    # Location Management
    path('dashboard/<uuid:shop_id>/location/', views.update_shop_location, name='update_location'),
    
    # API Endpoints
    path('api/geocode/', api_views.geocode, name='api_geocode'),
    path('api/search/', api_views.search_locations, name='api_search'),
    path('api/markers/', api_views.shop_markers, name='api_markers'),
    path('api/<uuid:shop_id>/update-location/', api_views.update_shop_location, name='api_update_location'),
]

