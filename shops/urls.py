from django.urls import path
from . import views
from . import settings_views

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
]

