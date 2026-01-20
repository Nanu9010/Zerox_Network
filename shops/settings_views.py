from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Shop

@login_required
def shop_settings(request):
    try:
        shop = request.user.shop
    except Shop.DoesNotExist:
        return redirect('shops:register')
        
    if request.method == 'POST':
        opening = request.POST.get('opening_time')
        closing = request.POST.get('closing_time')
        
        if not opening or not closing:
             # Logic to clear times? Or require them? Let's say optional
             pass
             
        shop.opening_time = opening if opening else None
        shop.closing_time = closing if closing else None
        shop.save()
        messages.success(request, 'Shop timings updated!')
        return redirect('shops:dashboard')
        
    return render(request, 'shops/settings.html', {'shop': shop})
