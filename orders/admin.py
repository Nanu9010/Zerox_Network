from django.contrib import admin
from .models import Order, Dispute, Refund, AuditLog

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_phone', 'shop', 'status', 'total_price', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['customer_phone', 'shop__name']

@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'issue_type', 'status', 'refund_approved', 'created_at']
    list_filter = ['status', 'issue_type', 'refund_approved']

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'amount', 'reason', 'status', 'created_at']
    list_filter = ['status', 'reason']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__username', 'action']
