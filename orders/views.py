from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from shops.models import Shop
from .models import Order, OrderFile, Dispute, Refund
import json

# Try to import PyPDF2 for page counting
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

def upload_file(request, shop_id):
    """Step 2: File upload (Batch Support)"""
    shop = get_object_or_404(Shop, id=shop_id, is_approved=True)
    
    if request.method == 'POST':
        # Get list of files (from multiple input)
        files = request.FILES.getlist('files')
        phone = request.POST.get('phone')
        customer_name = request.POST.get('customer_name', '')
        
        if not files:
            messages.error(request, 'Please upload at least one file.')
            return redirect('shops:detail', shop_id=shop_id)
        
        # Create Order Container
        order = Order.objects.create(
            shop=shop,
            customer=request.user if request.user.is_authenticated else None,
            customer_phone=phone,
            customer_name=customer_name,
            status='PENDING'
        )
        
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
        
        for uploaded_file in files:
            ext = uploaded_file.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                continue # Skip invalid files
            
            # Estimate pages
            pages = 1
            if ext == 'pdf' and PyPDF2:
                try:
                    reader = PyPDF2.PdfReader(uploaded_file)
                    pages = len(reader.pages)
                except:
                    pass
            
            OrderFile.objects.create(
                order=order,
                file=uploaded_file,
                file_name=uploaded_file.name,
                file_size_mb=round(uploaded_file.size / (1024 * 1024), 2),
                pages_count=pages
            )
        
        if not order.files.exists():
            order.delete()
            messages.error(request, 'No valid files uploaded.')
            return redirect('shops:detail', shop_id=shop_id)

        return redirect('orders:configure', order_id=order.id)
    
    return redirect('shops:detail', shop_id=shop_id)


def configure_order(request, order_id):
    """Step 3: Configure print settings (Multi-File Support)"""
    order = get_object_or_404(Order, id=order_id)
    files = order.files.all()
    
    if request.method == 'POST':
        apply_to_all = request.POST.get('apply_to_all') == 'on'
        
        if apply_to_all:
            # Common settings
            common_settings = {
                'pages_per_sheet': int(request.POST.get('pages_per_sheet', 1)),
                'print_type': request.POST.get('print_type', 'ALL'),
                'paper_size': request.POST.get('paper_size', 'A4'),
                'color_type': request.POST.get('color_type', 'BW'),
                'print_side': request.POST.get('print_side', 'SINGLE'),
                'copies': int(request.POST.get('copies', 1)),
                'special_note': request.POST.get('special_note', '')
            }
            
            for f in files:
                for key, value in common_settings.items():
                    setattr(f, key, value)
                f.save()
        else:
            # Per-file settings
            for f in files:
                prefix = f'file_{f.id}_'
                f.pages_per_sheet = int(request.POST.get(prefix + 'pages_per_sheet', 1))
                f.print_type = request.POST.get(prefix + 'print_type', 'ALL')
                f.paper_size = request.POST.get(prefix + 'paper_size', 'A4')
                f.color_type = request.POST.get(prefix + 'color_type', 'BW')
                f.print_side = request.POST.get(prefix + 'print_side', 'SINGLE')
                f.copies = int(request.POST.get(prefix + 'copies', 1))
                f.special_note = request.POST.get(prefix + 'special_note', '')
                f.save()
        
        # Calculate totals
        order.calculate_totals()
        
        # Handle Note for whole order if needed, but we stored per file. 
        # Maybe store a general note on order too? User said "Special note" in "Settings Panel".
        # If "Apply to all", note goes to all files.
        
        return redirect('orders:checkout', order_id=order.id)
    
    context = {
        'order': order,
        'shop': order.shop,
        'files': files
    }
    return render(request, 'orders/configure.html', context)


@csrf_exempt
def add_files_to_order(request, order_id):
    """AJAX endpoint to add more files to an existing order"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        order = get_object_or_404(Order, id=order_id)
        files = request.FILES.getlist('files')
        
        if not files:
            return JsonResponse({'success': False, 'error': 'No files uploaded'})
        
        added_files = []
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
        
        for uploaded_file in files:
            ext = uploaded_file.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                continue
            
            # Estimate pages
            pages = 1
            if ext == 'pdf' and PyPDF2:
                try:
                    reader = PyPDF2.PdfReader(uploaded_file)
                    pages = len(reader.pages)
                except:
                    pass
            
            order_file = OrderFile.objects.create(
                order=order,
                file=uploaded_file,
                file_name=uploaded_file.name,
                file_size_mb=round(uploaded_file.size / (1024 * 1024), 2),
                pages_count=pages
            )
            
            added_files.append({
                'id': order_file.id,
                'file_name': order_file.file_name,
                'file_url': order_file.file.url,
                'pages_count': order_file.pages_count,
                'file_size_mb': order_file.file_size_mb
            })
        
        return JsonResponse({
            'success': True,
            'files': added_files,
            'message': f'{len(added_files)} file(s) added successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def checkout(request, order_id):
    """Step 4: Checkout page"""
    order = get_object_or_404(Order, id=order_id)
    
    # Calculate amount in paise for Razorpay
    razorpay_amount = int(order.total_price * 100)
    
    context = {
        'order': order,
        'razorpay_amount': razorpay_amount,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID
    }
    return render(request, 'orders/checkout.html', context)


@csrf_exempt
def payment_success(request, order_id):
    """Handle successful Razorpay payment"""
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        
        try:
            data = json.loads(request.body)
            payment_id = data.get('razorpay_payment_id')
            
            # Mark order as paid
            order.mark_paid()
            order.payment_id = payment_id
            order.save()
            
            return JsonResponse({'success': True, 'order_id': str(order.id)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


def process_payment(request, order_id):
    """Legacy: Process payment (kept for backward compatibility)"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        payment_status = request.POST.get('payment_status', 'success')
        
        if payment_status == 'success':
            order.mark_paid()
            messages.success(request, f'Payment successful! Order #{order.id} confirmed.')
            return redirect('orders:my_orders')
        else:
            order.status = 'CANCELLED'
            order.save()
            messages.error(request, 'Payment failed. Please try again.')
            return redirect('core:home')
    
    return redirect('orders:checkout', order_id=order_id)


def my_orders(request):
    """Step 5: Customer order tracking dashboard"""
    # Get orders by phone if not logged in, or by user if logged in
    if request.user.is_authenticated:
        orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    else:
        # Fallback: session-based (simplified)
        orders = []
    
    context = {'orders': orders}
    return render(request, 'orders/my_orders.html', context)



def pickup_info(request, order_id):
    """Step 6: Simple pickup info page with huge PIN"""
    order = get_object_or_404(Order, id=order_id)
    
    # Gate: Only show if READY or COMPLETED
    if order.status not in ['READY', 'COMPLETED']:
        messages.error(request, 'Order is not ready for pickup yet.')
        return redirect('orders:my_orders')
        
    return render(request, 'orders/pickup.html', {'order': order})


def verify_pin(request):
    """Step 7: Verify PIN for pickup (used by shop)"""
    if request.method == 'POST':
        pin = request.POST.get('pin')
        # order_id optional if pin is unique enough in context of shop
        order_id = request.POST.get('order_id')
        
        try:
            if order_id:
                order = Order.objects.get(id=order_id, pin_code=pin, status='READY')
            else:
                # Find by PIN for this shop
                # Assuming shop owner is logged in
                if not getattr(request.user, 'shop', None):
                     messages.error(request, 'You must be a shop owner.')
                     return redirect('shops:dashboard')
                
                # STRICT: Ensure order belongs to logged in shop
                order = Order.objects.filter(shop=request.user.shop, pin_code=pin, status='READY').first()
                if not order:
                    raise Order.DoesNotExist
            
            # Additional check if order_id was passed
            if order_id and order.shop != request.user.shop:
                 messages.error(request, 'Unauthorized for this order.')
                 return redirect('shops:dashboard')

            order.complete_order()
            messages.success(request, f'Order #{order.id} verified and completed!')
        except Order.DoesNotExist:
            messages.error(request, 'Invalid PIN or order not ready.')
    
    return redirect('shops:dashboard')


@login_required
def raise_dispute(request, order_id):
    """Raise a dispute for a completed order - Case B"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    if order.status != 'COMPLETED':
        messages.error(request, 'Disputes can only be raised for completed orders.')
        return redirect('orders:my_orders')
        
    if not order.can_raise_dispute():
        messages.error(request, 'Dispute window has expired (48 hours after pickup).')
        return redirect('orders:my_orders')
        
    if request.method == 'POST':
        issue_type = request.POST.get('issue_type')
        description = request.POST.get('description')
        proof = request.FILES.get('proof_image')
        
        if not issue_type or not description or not proof:
            messages.error(request, 'All fields are required.')
        else:
            from .models import Dispute
            Dispute.objects.create(
                order=order,
                raised_by=request.user,
                issue_type=issue_type,
                description=description,
                proof_image=proof
            )
            # Notify admin logic (omitted for MVP)
            messages.success(request, 'Dispute raised successfully. We will review it shortly.')
            return redirect('orders:my_orders')
            
    return render(request, 'orders/raise_dispute.html', {'order': order})
