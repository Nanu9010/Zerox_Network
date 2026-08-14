"""
Bank Details Views for Shop Owners
Allow shop owners to add/edit their bank details for payouts
"""
import re
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .models import Shop, BankDetails


def validate_ifsc(ifsc):
    """Validate IFSC code format"""
    pattern = r'^[A-Z]{4}0[A-Z0-9]{6}$'
    return bool(re.match(pattern, ifsc.upper()))


def validate_account_number(account):
    """Validate account number (9-18 digits)"""
    return bool(re.match(r'^\d{9,18}$', account))


@login_required
def bank_details(request):
    """Shop owner bank details form"""
    shop = request.user.shops.first()
    if not shop:
        messages.error(request, 'You do not have a shop registered!')
        return redirect('shops:register')
    
    # Get existing bank details or create new
    bank_details, created = BankDetails.objects.get_or_create(shop=shop)
    
    if request.method == 'POST':
        account_holder_name = request.POST.get('account_holder_name', '').strip()
        bank_account_number = request.POST.get('bank_account_number', '').strip()
        confirm_account = request.POST.get('confirm_account', '').strip()
        ifsc_code = request.POST.get('ifsc_code', '').strip().upper()
        upi_id = request.POST.get('upi_id', '').strip()
        bank_name = request.POST.get('bank_name', '').strip()
        
        # Validation
        errors = []
        
        if not account_holder_name:
            errors.append('Account holder name is required.')
        
        if not bank_account_number:
            errors.append('Bank account number is required.')
        elif not validate_account_number(bank_account_number):
            errors.append('Invalid account number format (9-18 digits).')
        
        if bank_account_number != confirm_account:
            errors.append('Account numbers do not match.')
        
        if not ifsc_code:
            errors.append('IFSC code is required.')
        elif not validate_ifsc(ifsc_code):
            errors.append('Invalid IFSC code format (e.g., HDFC0001234).')
        
        if upi_id and not re.match(r'^[\w\.\-]+@[\w]+$', upi_id):
            errors.append('Invalid UPI ID format (e.g., name@upi).')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'shops/bank_details.html', {
                'shop': shop,
                'bank_details': bank_details,
                'form_data': request.POST
            })
        
        # Save bank details
        bank_details.account_holder_name = account_holder_name
        bank_details.bank_account_number = bank_account_number
        bank_details.ifsc_code = ifsc_code
        bank_details.upi_id = upi_id if upi_id else None
        bank_details.bank_name = bank_name
        bank_details.is_verified = False  # Require re-verification on change
        bank_details.save()
        
        messages.success(request, 'Bank details saved successfully! Verification will be done shortly.')
        return redirect('shops:payout_history')
    
    # Get payout history for this shop
    from orders.models import Payout
    recent_payouts = Payout.objects.filter(shop=shop)[:10]
    
    # Calculate pending amount
    completed_orders = shop.orders.filter(status='COMPLETED')
    total_earned = completed_orders.aggregate(Sum('shop_payout'))['shop_payout__sum'] or 0
    pending_amount = float(total_earned) - float(shop.paid_total)
    
    context = {
        'shop': shop,
        'bank_details': bank_details,
        'recent_payouts': recent_payouts,
        'pending_amount': pending_amount,
        'total_earned': total_earned,
    }
    return render(request, 'shops/bank_details.html', context)


@login_required
def payout_history(request):
    """Shop owner payout history"""
    shop = request.user.shops.first()
    if not shop:
        messages.error(request, 'You do not have a shop registered!')
        return redirect('shops:register')
    
    from orders.models import Payout
    payouts = Payout.objects.filter(shop=shop).order_by('-payout_date')
    
    # Calculate totals
    total_paid = payouts.filter(status='COMPLETED').aggregate(Sum('amount'))['amount__sum'] or 0
    pending_payouts = payouts.filter(status__in=['PENDING', 'PROCESSING']).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Pending balance
    completed_orders = shop.orders.filter(status='COMPLETED')
    total_earned = completed_orders.aggregate(Sum('shop_payout'))['shop_payout__sum'] or 0
    pending_balance = float(total_earned) - float(shop.paid_total)
    
    context = {
        'shop': shop,
        'payouts': payouts,
        'total_paid': total_paid,
        'pending_payouts': pending_payouts,
        'pending_balance': pending_balance,
        'total_earned': total_earned,
    }
    return render(request, 'shops/payout_history.html', context)