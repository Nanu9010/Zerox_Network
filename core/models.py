from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """Extended user profile with role-based permissions"""
    
    ROLE_CHOICES = [
        ('CUSTOMER', 'Customer'),
        ('SHOP', 'Shop Owner'),
        ('STAFF', 'Staff'),
        ('ADMIN', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='CUSTOMER')
    is_shop_owner = models.BooleanField(default=False, help_text="User also owns shops (dual role: Customer + Shop Owner)")
    phone = models.CharField(max_length=15)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} ({self.role})"
    
    class Meta:
        ordering = ['-created_at']


class Notification(models.Model):
    """User notifications for order updates, shop alerts, etc."""
    
    TYPE_CHOICES = [
        ('ORDER_UPDATE', 'Order Update'),
        ('SHOP_ALERT', 'Shop Alert'),
        ('SYSTEM', 'System'),
        ('PROMOTION', 'Promotion'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='SYSTEM')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, help_text="Optional URL to redirect on click")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"[{self.notification_type}] {self.title} -> {self.user.username}"
    
    class Meta:
        ordering = ['-created_at']
