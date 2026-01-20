from django.contrib import admin
from .models import Shop

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'is_approved', 'is_suspended', 'rating', 'total_orders']
    list_filter = ['is_approved', 'is_suspended', 'created_at']
    search_fields = ['name', 'location', 'phone']
    actions = ['approve_shops', 'suspend_shops']
    
    def approve_shops(self, request, queryset):
        queryset.update(is_approved=True, is_verified=True)
        self.message_user(request, f"{queryset.count()} shops approved.")
    approve_shops.short_description = "Approve selected shops"
    
    def suspend_shops(self, request, queryset):
        queryset.update(is_suspended=True)
        self.message_user(request, f"{queryset.count()} shops suspended.")
    suspend_shops.short_description = "Suspend selected shops"
