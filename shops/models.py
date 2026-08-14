from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from math import radians, cos, sin, asin, sqrt
import uuid


class Shop(models.Model):
    """Shop model for print shop registration"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shops')
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=300)
    phone = models.CharField(max_length=15)
    
    # Location Coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Shop latitude coordinate")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Shop longitude coordinate")
    
    # Approval & Status
    is_verified = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True)
    suspension_reason = models.TextField(blank=True)
    
    qr_code = models.CharField(max_length=100, unique=True, editable=False)
    
    # Price List (per page)
    a4_bw_price = models.DecimalField(max_digits=6, decimal_places=2, default=1.00)
    a4_color_price = models.DecimalField(max_digits=6, decimal_places=2, default=5.00)
    a3_bw_price = models.DecimalField(max_digits=6, decimal_places=2, default=2.00)
    a3_color_price = models.DecimalField(max_digits=6, decimal_places=2, default=10.00)
    
    # Analytics
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_orders = models.IntegerField(default=0)
    avg_print_time = models.IntegerField(default=15, help_text="Average print time in minutes")
    
    # Earnings
    earnings_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Lifetime gross earnings")
    paid_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Total amount already paid out to shop")
    commission_rate = models.DecimalField(max_digits=4, decimal_places=2, default=15.00, help_text="Platform commission percentage")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.qr_code:
            self.qr_code = f"SHOP-{str(self.id)[:8].upper()}"
        super().save(*args, **kwargs)
    
    # Shop Timings
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    def is_active(self):
        """Shop is active if approved and not suspended"""
        return self.is_approved and not self.is_suspended

    @property
    def is_open(self):
        """Check if shop is currently open based on time"""
        if not self.opening_time or not self.closing_time:
            return True
            
        now = timezone.localtime().time()
        if self.opening_time < self.closing_time:
            return self.opening_time <= now <= self.closing_time
        else:
            return now >= self.opening_time or now <= self.closing_time
    
    def calculate_commission(self, amount):
        """Calculate platform commission"""
        return (amount * self.commission_rate) / 100
    
    def get_primary_image(self):
        """Get the primary image for the shop or return placeholder"""
        primary = self.images.filter(is_primary=True, is_approved=True).first()
        if primary:
            return primary.image.url
        any_img = self.images.filter(is_approved=True).first()
        if any_img:
            return any_img.image.url
        return '/static/images/shop_placeholder.png'

    def get_images(self):
        """Get all approved images"""
        return self.images.filter(is_approved=True)

    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        """Calculate distance in km between two points using Haversine formula"""
        lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return round(km, 1)

    def distance_from(self, lat, lon):
        """Calculate distance from given coordinates"""
        if self.latitude and self.longitude:
            return self.haversine(lat, lon, self.latitude, self.longitude)
        return None

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']


class ShopImage(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='shop_images/')
    caption = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.is_primary:
            # Ensure only one primary image per shop
            ShopImage.objects.filter(shop=self.shop, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.shop.name}"


class BankDetails(models.Model):
    """Bank details for shop owner payouts"""
    
    shop = models.OneToOneField(Shop, on_delete=models.CASCADE, related_name='bank_details')
    account_holder_name = models.CharField(max_length=200)
    bank_account_number = models.CharField(max_length=20)
    ifsc_code = models.CharField(max_length=11)
    upi_id = models.CharField(max_length=100, blank=True, null=True)
    bank_name = models.CharField(max_length=200, blank=True)
    
    # Razorpay IDs
    razorpay_contact_id = models.CharField(max_length=50, blank=True)
    razorpay_fund_account_id = models.CharField(max_length=50, blank=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Bank Details for {self.shop.name} ({self.ifsc_code})"
    
    class Meta:
        verbose_name_plural = "Bank Details"
