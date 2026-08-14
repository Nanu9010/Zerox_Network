"""
Razorpay Payouts API Integration
Handles contact creation, fund account setup, and payout processing
"""
import razorpay
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_client():
    """Get Razorpay client with API keys"""
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_contact(shop, bank_details):
    """
    Create a contact on RazorpayX for the shop owner
    Returns: contact_id or None on failure
    """
    client = get_client()
    
    try:
        contact = client.contact.create({
            'name': bank_details.account_holder_name,
            'email': shop.owner.email,
            'contact': bank_details.shop.phone,
            'type': 'vendor',
            'reference_id': str(shop.id),
            'notes': {
                'shop_name': shop.name,
                'shop_id': str(shop.id)
            }
        })
        
        contact_id = contact.get('id')
        logger.info(f"Created Razorpay contact {contact_id} for shop {shop.name}")
        return contact_id
        
    except Exception as e:
        logger.error(f"Failed to create Razorpay contact for shop {shop.name}: {str(e)}")
        return None


def create_fund_account(contact_id, bank_details):
    """
    Create a fund account (bank account) for the contact
    Returns: fund_account_id or None on failure
    """
    client = get_client()
    
    fund_account_data = {
        'contact_id': contact_id,
        'account_type': 'bank_account',
        'bank_account': {
            'name': bank_details.account_holder_name,
            'ifsc': bank_details.ifsc_code,
            'account_number': bank_details.bank_account_number
        }
    }
    
    try:
        fund_account = client.fund_account.create(fund_account_data)
        fund_account_id = fund_account.get('id')
        logger.info(f"Created fund account {fund_account_id} for contact {contact_id}")
        return fund_account_id
        
    except Exception as e:
        logger.error(f"Failed to create fund account for contact {contact_id}: {str(e)}")
        return None


def create_payout(bank_details, amount, mode='IMPS', reference_id=None):
    """
    Create a payout to the shop's bank account
    
    Args:
        bank_details: BankDetails model instance
        amount: Amount in INR (will be converted to paise)
        mode: NEFT, RTGS, IMPS, or UPI
        reference_id: Optional reference ID
    
    Returns:
        dict with payout_id and status, or None on failure
    """
    client = get_client()
    
    # Convert amount to paise (minimum 100 paise = ₹1)
    amount_in_paise = int(amount * 100)
    if amount_in_paise < 100:
        logger.warning(f"Payout amount ₹{amount} is less than minimum ₹1")
        return None
    
    # Use fund account ID if available, otherwise use bank details directly
    if bank_details.razorpay_fund_account_id:
        fund_account_id = bank_details.razorpay_fund_account_id
    else:
        # Need to create contact and fund account first
        if not bank_details.razorpay_contact_id:
            contact_id = create_contact(bank_details.shop, bank_details)
            if not contact_id:
                return None
            bank_details.razorpay_contact_id = contact_id
            bank_details.save()
        
        fund_account_id = create_fund_account(
            bank_details.razorpay_contact_id,
            bank_details
        )
        if not fund_account_id:
            return None
        bank_details.razorpay_fund_account_id = fund_account_id
        bank_details.save()
    
    payout_data = {
        'account_number': settings.RAZORPAYX_ACCOUNT_NUMBER,
        'fund_account_id': fund_account_id,
        'amount': amount_in_paise,
        'currency': 'INR',
        'mode': mode,
        'purpose': 'payout',
        'queue_if_low_balance': True,
        'reference_id': reference_id or f"ZEROX-{bank_details.shop.id}",
        'narration': f"Payout to {bank_details.shop.name}",
        'notes': {
            'shop_id': str(bank_details.shop.id),
            'shop_name': bank_details.shop.name
        }
    }
    
    try:
        payout = client.payout.create(payout_data)
        payout_id = payout.get('id')
        status = payout.get('status')
        
        logger.info(f"Created payout {payout_id} for shop {bank_details.shop.name}: ₹{amount} ({status})")
        
        return {
            'payout_id': payout_id,
            'status': status,
            'utr': payout.get('utr'),
            'amount': amount,
            'mode': mode
        }
        
    except Exception as e:
        logger.error(f"Failed to create payout for shop {bank_details.shop.name}: {str(e)}")
        return None