"""
API views for shop geocoding and map features
"""
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from .geocoding import geocode_address, search_places


@require_GET
def geocode(request):
    """Convert address to coordinates"""
    address = request.GET.get('address', '').strip()
    
    if not address:
        return JsonResponse({'error': 'Address is required'}, status=400)
    
    result = geocode_address(address)
    
    if result:
        return JsonResponse({
            'success': True,
            'lat': result['lat'],
            'lon': result['lon'],
            'display_name': result['display_name']
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'Could not geocode address'
        }, status=404)


@require_GET
def search_locations(request):
    """Search for places with autocomplete"""
    query = request.GET.get('q', '').strip()
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    results = search_places(query, lat, lon)
    
    return JsonResponse({
        'results': results
    })


@require_GET
def shop_markers(request):
    """Get all approved shops as map markers"""
    from .models import Shop
    
    shops = Shop.objects.filter(
        is_approved=True,
        is_suspended=False,
        latitude__isnull=False,
        longitude__isnull=False
    ).values('id', 'name', 'location', 'latitude', 'longitude', 'a4_bw_price', 'rating')
    
    markers = [{
        'id': str(shop['id']),
        'name': shop['name'],
        'location': shop['location'],
        'lat': float(shop['latitude']),
        'lon': float(shop['longitude']),
        'price': float(shop['a4_bw_price']),
        'rating': float(shop['rating'])
    } for shop in shops]
    
    return JsonResponse({'markers': markers})


@login_required
@require_POST
def update_shop_location(request, shop_id):
    """Update shop location via AJAX"""
    import json
    from .models import Shop
    
    try:
        shop = Shop.objects.get(id=shop_id, owner=request.user)
    except Shop.DoesNotExist:
        return JsonResponse({'error': 'Shop not found or unauthorized'}, status=404)
    
    try:
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        location = data.get('location', shop.location)
        
        if latitude is not None and longitude is not None:
            shop.latitude = float(latitude)
            shop.longitude = float(longitude)
            shop.location = location
            shop.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Location updated successfully',
                'latitude': shop.latitude,
                'longitude': shop.longitude,
                'location': shop.location
            })
        else:
            return JsonResponse({'error': 'Invalid coordinates'}, status=400)
            
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({'error': str(e)}, status=400)