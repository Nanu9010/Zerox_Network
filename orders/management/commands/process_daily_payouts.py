"""
Management command to process daily payouts to shop owners
Run manually or via cron/scheduler
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum
from datetime import date
import logging

from shops.models import Shop, BankDetails
from orders.models import Payout, AuditLog
from admin_portal.models import PayoutConfig
from shops.razorpay_payout import create_payout

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process daily payouts to shop owners based on completed orders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be paid without actually processing',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force payout even if not scheduled time',
        )

    def handle(self, *args, **options):
        today = date.today()
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"  DAILY PAYOUT PROCESSING - {today}")
        self.stdout.write(f"{'='*60}\n")
        
        # Load payout config
        config = PayoutConfig.load()
        
        # Check if payouts are enabled
        if not config.payout_enabled and not force:
            self.stdout.write(self.style.WARNING(
                "Payouts are disabled. Use --force to run anyway."
            ))
            return
        
        # Check if today is a payout day
        today_weekday = today.weekday()  # 0=Monday, 6=Sunday
        allowed_days = [int(d.strip()) for d in config.payout_days.split(',')]
        
        if today_weekday not in allowed_days and not force:
            self.stdout.write(self.style.WARNING(
                f"Today (day {today_weekday}) is not a payout day. Allowed days: {allowed_days}"
            ))
            return
        
        # Get all approved shops with verified bank details
        shops = Shop.objects.filter(
            is_approved=True,
            is_suspended=False,
            bank_details__isnull=False,
            bank_details__is_verified=True
        ).select_related('bank_details')
        
        if not shops.exists():
            self.stdout.write(self.style.WARNING("No shops with verified bank details found."))
            return
        
        total_payouts = 0
        total_amount = 0
        failed_payouts = 0
        
        for shop in shops:
            # Calculate pending balance
            completed_orders = shop.orders.filter(status='COMPLETED')
            total_earned = completed_orders.aggregate(
                Sum('shop_payout')
            )['shop_payout__sum'] or 0
            
            pending_balance = float(total_earned) - float(shop.paid_total)
            
            if pending_balance <= 0:
                self.stdout.write(f"  {shop.name}: No pending balance (earned: ₹{total_earned}, paid: ₹{shop.paid_total})")
                continue
            
            self.stdout.write(f"\n  Processing: {shop.name}")
            self.stdout.write(f"    Total Earned: ₹{total_earned}")
            self.stdout.write(f"    Already Paid: ₹{shop.paid_total}")
            self.stdout.write(f"    Pending:      ₹{pending_balance}")
            
            if dry_run:
                self.stdout.write(self.style.SUCCESS(f"    [DRY RUN] Would pay: ₹{pending_balance}"))
                total_payouts += 1
                total_amount += pending_balance
                continue
            
            # Create payout record
            payout = Payout.objects.create(
                shop=shop,
                amount=pending_balance,
                status='PENDING',
                mode=config.payout_mode,
                payout_date=today
            )
            
            # Process payout via Razorpay
            result = create_payout(
                bank_details=shop.bank_details,
                amount=pending_balance,
                mode=config.payout_mode,
                reference_id=f"ZEROX-{shop.id}-{today.strftime('%Y%m%d')}"
            )
            
            if result:
                payout.razorpay_payout_id = result['payout_id']
                payout.status = 'PROCESSING'
                payout.processed_at = timezone.now()
                payout.save()
                
                # Update shop paid_total
                shop.paid_total = float(shop.paid_total) + pending_balance
                shop.save()
                
                # Audit log
                AuditLog.objects.create(
                    action='PAYOUT_PROCESSED',
                    model_name='Payout',
                    object_id=str(payout.id),
                    details=f"Payout of ₹{pending_balance} processed for {shop.name} via {config.payout_mode}"
                )
                
                self.stdout.write(self.style.SUCCESS(
                    f"    Payout created: {result['payout_id']} (Status: {result['status']})"
                ))
                total_payouts += 1
                total_amount += pending_balance
            else:
                payout.status = 'FAILED'
                payout.failure_reason = 'Razorpay API call failed'
                payout.save()
                
                AuditLog.objects.create(
                    action='PAYOUT_FAILED',
                    model_name='Payout',
                    object_id=str(payout.id),
                    details=f"Payout of ₹{pending_balance} failed for {shop.name}"
                )
                
                self.stdout.write(self.style.ERROR(f"    Payout FAILED for {shop.name}"))
                failed_payouts += 1
        
        # Summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"  SUMMARY")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"  Total Payouts: {total_payouts}")
        self.stdout.write(f"  Total Amount:  ₹{total_amount}")
        self.stdout.write(f"  Failed:        {failed_payouts}")
        self.stdout.write(f"{'='*60}\n")