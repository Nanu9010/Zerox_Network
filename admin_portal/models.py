from django.db import models


class PayoutConfig(models.Model):
    """Payout configuration (singleton model)"""
    
    MODE_CHOICES = [
        ('NEFT', 'NEFT'),
        ('RTGS', 'RTGS'),
        ('IMPS', 'IMPS'),
        ('UPI', 'UPI'),
    ]
    
    payout_enabled = models.BooleanField(default=False)
    payout_hour = models.IntegerField(default=6, help_text="Hour to run payouts (0-23)")
    payout_minute = models.IntegerField(default=0, help_text="Minute to run payouts (0-59)")
    payout_mode = models.CharField(max_length=10, choices=MODE_CHOICES, default='IMPS')
    payout_days = models.CharField(
        max_length=50,
        default='0,1,2,3,4,5,6',
        help_text="Comma-separated day numbers (0=Monday, 6=Sunday)"
    )
    
    # RazorpayX Configuration
    razorpayx_account_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="RazorpayX business account number for debiting"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Payout Config (Enabled: {self.payout_enabled}, Time: {self.payout_hour}:{self.payout_minute:02d})"
    
    class Meta:
        verbose_name = "Payout Configuration"
        verbose_name_plural = "Payout Configuration"
    
    def save(self, *args, **kwargs):
        # Singleton pattern - only allow one instance
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
