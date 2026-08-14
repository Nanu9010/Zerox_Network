"""
Geocoding utility for converting addresses to coordinates
Uses Nominatim (OpenStreetMap) - free, no API key required
"""
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Nominatim API (free, no key needed)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "ZeroxNetwork/1.0"


def geocode_address(address):
    """
    Convert address to latitude/longitude using Nominatim
    
    Args:
        address: Street address string
        
    Returns:
        dict with 'lat', 'lon', 'display_name' or None
    """
    try:
        params = {
            'q': address,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        headers = {'User-Agent': USER_AGENT}
        
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        results = response.json()
        
        if results:
            return {
                'lat': float(results[0]['lat']),
                'lon': float(results[0]['lon']),
                'display_name': results[0].get('display_name', address)
            }
        return None
        
    except Exception as e:
        logger.error(f"Geocoding failed for '{address}': {str(e)}")
        return None


def search_places(query, lat=None, lon=None, limit=5):
    """
    Search for places/addresses with autocomplete
    
    Args:
        query: Search query
        lat: Bias towards this latitude (optional)
        lon: Bias towards this longitude (optional)
        limit: Max results
        
    Returns:
        list of place results
    """
    try:
        params = {
            'q': query,
            'format': 'json',
            'limit': limit,
            'addressdetails': 1
        }
        
        if lat and lon:
            params['viewbox'] = f"{lon-0.1},{lat+0.1},{lon+0.1},{lat-0.1}"
            params['bounded'] = 0
        
        headers = {'User-Agent': USER_AGENT}
        
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        results = response.json()
        
        return [{
            'lat': float(r['lat']),
            'lon': float(r['lon']),
            'display_name': r.get('display_name', ''),
            'name': r.get('name', query),
            'type': r.get('type', ''),
            'address': r.get('address', {})
        } for r in results]
        
    except Exception as e:
        logger.error(f"Place search failed for '{query}': {str(e)}")
        return []