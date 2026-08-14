from django import forms
from .models import ShopImage
from django.core.exceptions import ValidationError
from PIL import Image

class ShopImageForm(forms.ModelForm):
    class Meta:
        model = ShopImage
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., Shop Front View'}),
            'image': forms.FileInput(attrs={'class': 'form-input', 'accept': 'image/*', 'required': 'required'})
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Check size (5MB limit)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("Image file too large (Max 5MB)")
            
            # Check resolution
            try:
                img = Image.open(image)
                width, height = img.size
                if width < 1280 or height < 720:
                     raise ValidationError(f"Image resolution too low ({width}x{height}). Minimum 1280x720 required.")
            except ImportError:
                # If PIL not installed (though Django ImageField usually requires it), skip check
                pass
            except Exception as e:
                # Corrupt image or other error
                raise ValidationError("Invalid image file.")
                
        return image
