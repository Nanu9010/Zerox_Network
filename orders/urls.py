from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('upload/<uuid:shop_id>/', views.upload_file, name='upload'),
    path('configure/<int:order_id>/', views.configure_order, name='configure'),
    path('add-files/<int:order_id>/', views.add_files_to_order, name='add_files'),
    path('checkout/<int:order_id>/', views.checkout, name='checkout'),
    path('payment/<int:order_id>/', views.process_payment, name='payment'),
    path('payment/success/<int:order_id>/', views.payment_success, name='payment_success'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('pickup/<int:order_id>/', views.pickup_info, name='pickup_info'),
    path('verify-pin/', views.verify_pin, name='verify_pin'),
    path('dispute/<int:order_id>/', views.raise_dispute, name='raise_dispute'),
]
