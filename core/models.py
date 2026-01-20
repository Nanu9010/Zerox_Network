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
    phone = models.CharField(max_length=15)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} ({self.role})"
    
    class Meta:
        ordering = ['-created_at']
