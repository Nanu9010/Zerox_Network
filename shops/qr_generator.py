"""
QR Code Generator for Zerox Network
Generates QR codes and downloadable posters for shops
"""
import qrcode
from io import BytesIO
from django.conf import settings
import os


def generate_shop_qr(shop, base_url="http://127.0.0.1:8000"):
    """Generate QR code for a shop's unique profile page"""
    
    # Shop's unique URL
    shop_url = f"{base_url}/shop/{shop.qr_code}/"
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(shop_url)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="#00B140", back_color="white")
    
    # Save to media folder
    qr_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes')
    os.makedirs(qr_dir, exist_ok=True)
    
    qr_filename = f"{shop.qr_code}.png"
    qr_path = os.path.join(qr_dir, qr_filename)
    
    img.save(qr_path)
    
    return f"qr_codes/{qr_filename}"


def get_qr_image_bytes(shop, base_url="http://127.0.0.1:8000"):
    """Get QR code as bytes for embedding in PDF"""
    
    shop_url = f"{base_url}/shop/{shop.qr_code}/"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(shop_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#00B140", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return buffer
