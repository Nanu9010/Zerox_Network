from django.db import models
from django.contrib.auth.models import User
from shops.models import Shop
import random
import math
from datetime import timedelta
from django.utils import timezone


class Order(models.Model):
    """Order model representing a print job (Container for multiple files)"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Payment'),
        ('PAID', 'Paid'),
        ('ACCEPTED', 'Accepted by Shop'),
        ('PRINTING', 'Printing'),
        ('READY', 'Ready for Pickup'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected by Shop'),
        ('REFUNDED', 'Refunded'),
    ]
    
    # Relations
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='orders')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=15)
    
    # Financials (Aggregated from OrderFiles)
    final_sheets = models.IntegerField(default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shop_payout = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    pin_code = models.CharField(max_length=4, blank=True, null=True)
    shop_proof_image = models.ImageField(upload_to='order_proofs/', null=True, blank=True)
    
    # Rejection reason (if applicable)
    rejection_reason = models.TextField(blank=True)
    
    # Deadlines
    pickup_deadline = models.DateTimeField(null=True, blank=True)
    dispute_window_expires = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def generate_pin(self):
        """Generate a random 4-digit PIN"""
        self.pin_code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        self.save()
        
    def calculate_totals(self):
        """Aggregate totals from all OrderFiles"""
        total = 0
        sheets = 0
        for file in self.files.all():
            file.calculate_price()
            total += file.total_price
            sheets += file.final_sheets
            
        self.total_price = total
        self.final_sheets = sheets
        
        # Calculate commission
        self.commission_amount = self.shop.calculate_commission(self.total_price)
        self.shop_payout = self.total_price - self.commission_amount
        self.save()

    def mark_paid(self):
        """Mark order as paid and set deadlines"""
        self.status = 'PAID'
        self.paid_at = timezone.now()
        self.pickup_deadline = timezone.now() + timedelta(days=7)
        self.save()

    def complete_order(self):
        """Mark order as completed (Pickup confirmed)"""
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        # Dispute window starts from pickup time
        self.dispute_window_expires = timezone.now() + timedelta(hours=48)
        self.save()
        
    def can_raise_dispute(self):
        """Check if dispute window is still open"""
        if not self.dispute_window_expires:
            return False
        return timezone.now() < self.dispute_window_expires
    
    def __str__(self):
        return f"Order #{self.id} - {self.customer_phone} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']


class OrderFile(models.Model):
    """Individual file within an order"""
    
    PAPER_SIZE_CHOICES = [('A4', 'A4'), ('A3', 'A3')]
    COLOR_CHOICES = [('BW', 'Black & White'), ('COLOR', 'Color')]
    SIDE_CHOICES = [('SINGLE', 'Single Side'), ('DOUBLE', 'Double Side')]
    
    PAGES_PER_SHEET_CHOICES = [
        (1, "1 page per sheet"),
        (2, "2 pages per sheet"),
        (4, "4 pages per sheet"),
        (6, "6 pages per sheet"),
        (9, "9 pages per sheet"),
    ]

    PRINT_TYPE_CHOICES = [
        ("ALL", "All pages"),
        ("ODD", "Odd pages only"),
        ("EVEN", "Even pages only"),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='uploads/orders/')
    file_name = models.CharField(max_length=255)
    file_size_mb = models.FloatField(default=0.0)
    pages_count = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Print Configuration (Per File)
    paper_size = models.CharField(max_length=2, choices=PAPER_SIZE_CHOICES, default='A4')
    color_type = models.CharField(max_length=10, choices=COLOR_CHOICES, default='BW')
    print_side = models.CharField(max_length=10, choices=SIDE_CHOICES, default='SINGLE')
    pages_per_sheet = models.IntegerField(choices=PAGES_PER_SHEET_CHOICES, default=1)
    print_type = models.CharField(max_length=10, choices=PRINT_TYPE_CHOICES, default="ALL")
    copies = models.PositiveIntegerField(default=1)
    special_note = models.TextField(blank=True, null=True)
    
    # Calculated Fields
    price_per_sheet = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    final_sheets = models.IntegerField(default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    def adjusted_pages(self):
        if self.print_type == "ODD":
            return (self.pages_count + 1) // 2
        elif self.print_type == "EVEN":
            return self.pages_count // 2
        return self.pages_count

    def sheets_after_micro(self, adj_pages):
        return math.ceil(adj_pages / self.pages_per_sheet)

    def final_sheet_count_calc(self, sheets):
        if self.print_side == 'DOUBLE':
            return math.ceil(sheets / 2)
        return sheets

    def calculate_price(self):
        shop = self.order.shop
        
        # Determine base price per SHEET
        if self.paper_size == 'A4' and self.color_type == 'BW':
            price = shop.a4_bw_price
        elif self.paper_size == 'A4' and self.color_type == 'COLOR':
            price = shop.a4_color_price
        elif self.paper_size == 'A3' and self.color_type == 'BW':
            price = shop.a3_bw_price
        elif self.paper_size == 'A3' and self.color_type == 'COLOR':
            price = shop.a3_color_price
        else:
            price = 0
        
        self.price_per_sheet = price
        
        # Logic Sequence
        adj_pages = self.adjusted_pages()
        micro_sheets = self.sheets_after_micro(adj_pages)
        sheets_per_copy = self.final_sheet_count_calc(micro_sheets)
        
        # Total
        self.final_sheets = sheets_per_copy * self.copies
        self.total_price = price * self.final_sheets
        self.save()
    
    def __str__(self):
        return f"{self.file_name} ({self.order.id})"


class Dispute(models.Model):
    """Dispute raised by customers"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('IN_REVIEW', 'Under Review'),
        ('RESOLVED', 'Resolved'),
        ('REJECTED', 'Rejected'),
    ]
    
    ISSUE_CHOICES = [
        ('MISSING_PAGES', 'Missing Pages'),
        ('WRONG_COLOR', 'Wrong Color'),
        ('WRONG_SIZE', 'Wrong Paper Size'),
        ('POOR_QUALITY', 'Poor Print Quality'),
        ('OTHER', 'Other'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='disputes')
    raised_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disputes')
    
    issue_type = models.CharField(max_length=20, choices=ISSUE_CHOICES)
    description = models.TextField()
    proof_image = models.ImageField(upload_to='disputes/', null=True, blank=True)
    
    # Shop response
    shop_response = models.TextField(blank=True)
    shop_proof_image = models.ImageField(upload_to='disputes/shop/', null=True, blank=True)
    
    # Admin decision
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    admin_decision = models.TextField(blank=True)
    refund_approved = models.BooleanField(default=False)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Dispute #{self.id} - Order #{self.order.id}"
    
    class Meta:
        ordering = ['-created_at']


class Refund(models.Model):
    """Refund processing"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    REASON_CHOICES = [
        ('PAYMENT_FAILED', 'Payment Failed'),
        ('SHOP_REJECTED', 'Shop Rejected Order'),
        ('SHOP_CLOSED', 'Shop Closed/Unavailable'),
        ('DISPUTE_APPROVED', 'Dispute Approved'),
        ('ADMIN_FORCED', 'Admin Forced Refund'),
        ('ORDER_EXPIRED', 'Order Expired'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Refund #{self.id} - ₹{self.amount}"
    
    class Meta:
        ordering = ['-created_at']


class AuditLog(models.Model):
    """System audit trail for all critical actions"""
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=50, blank=True)
    object_id = models.CharField(max_length=100, blank=True, null=True, default='')  # CharField for UUID support
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']
