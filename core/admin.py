from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone', 'is_blocked', 'created_at']
    list_filter = ['role', 'is_blocked']
    search_fields = ['user__username', 'phone']
    actions = ['block_users', 'unblock_users']
    
    def block_users(self, request, queryset):
        queryset.update(is_blocked=True)
        self.message_user(request, f"{queryset.count()} users blocked.")
    block_users.short_description = "Block selected users"
    
    def unblock_users(self, request, queryset):
        queryset.update(is_blocked=False)
        self.message_user(request, f"{queryset.count()} users unblocked.")
    unblock_users.short_description = "Unblock selected users"
