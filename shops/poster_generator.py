"""
PDF Poster Generator for Shop QR Codes
Creates downloadable A4 poster with shop info and QR code
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
from .qr_generator import get_qr_image_bytes


def generate_shop_poster(shop, base_url="http://127.0.0.1:8000"):
    """Generate A4 PDF poster for shop with QR code"""
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Colors
    primary_green = HexColor("#00B140")
    dark_text = HexColor("#1a1a2e")
    gray_text = HexColor("#6b7280")
    
    # Background - white with green header
    c.setFillColor(primary_green)
    c.rect(0, height - 3*cm, width, 3*cm, fill=True, stroke=False)
    
    # Header text
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width/2, height - 2*cm, "ZEROX NETWORK")
    
    # Shop name
    c.setFillColor(dark_text)
    c.setFont("Helvetica-Bold", 36)
    shop_name = shop.name.upper()
    c.drawCentredString(width/2, height - 5.5*cm, shop_name)
    
    # Location
    c.setFillColor(gray_text)
    c.setFont("Helvetica", 16)
    c.drawCentredString(width/2, height - 6.5*cm, f"📍 {shop.location}")
    
    # Tagline
    c.setFillColor(primary_green)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height - 9*cm, "📱 Scan & Send Your File")
    
    c.setFillColor(gray_text)
    c.setFont("Helvetica", 14)
    c.drawCentredString(width/2, height - 10*cm, "No app needed • Pay online • Quick pickup")
    
    # QR Code
    qr_buffer = get_qr_image_bytes(shop, base_url)
    qr_image = ImageReader(qr_buffer)
    qr_size = 8*cm
    qr_x = (width - qr_size) / 2
    qr_y = height - 20*cm
    c.drawImage(qr_image, qr_x, qr_y, width=qr_size, height=qr_size)
    
    # QR border
    c.setStrokeColor(primary_green)
    c.setLineWidth(3)
    c.rect(qr_x - 0.3*cm, qr_y - 0.3*cm, qr_size + 0.6*cm, qr_size + 0.6*cm, fill=False, stroke=True)
    
    # Shop URL
    shop_url = f"{base_url}/shop/{shop.qr_code}/"
    c.setFillColor(dark_text)
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, qr_y - 1*cm, shop_url)
    
    # Price box
    c.setFillColor(HexColor("#f0fdf4"))
    c.rect(2*cm, 3*cm, width - 4*cm, 4*cm, fill=True, stroke=False)
    c.setStrokeColor(primary_green)
    c.setLineWidth(1)
    c.rect(2*cm, 3*cm, width - 4*cm, 4*cm, fill=False, stroke=True)
    
    # Prices
    c.setFillColor(dark_text)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(3*cm, 6*cm, "💰 PRICING")
    
    c.setFont("Helvetica", 12)
    c.drawString(3*cm, 5.2*cm, f"A4 Black & White: ₹{shop.a4_bw_price}/page")
    c.drawString(3*cm, 4.5*cm, f"A4 Color: ₹{shop.a4_color_price}/page")
    c.drawString(10*cm, 5.2*cm, f"A3 Black & White: ₹{shop.a3_bw_price}/page")
    c.drawString(10*cm, 4.5*cm, f"A3 Color: ₹{shop.a3_color_price}/page")
    
    # Footer
    c.setFillColor(gray_text)
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, 1.5*cm, "Powered by Zerox Network • Fast, Easy, Paperless Printing")
    
    c.save()
    buffer.seek(0)
    
    return buffer


def generate_simple_qr_poster(shop, base_url="http://127.0.0.1:8000"):
    """Generate a simple QR poster without reportlab (fallback)"""
    
    # Just return the QR image bytes
    return get_qr_image_bytes(shop, base_url)
