from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Automatically create UserProfile for newly created User instances."""
    if created:
        role = 'ADMIN' if instance.is_superuser else ('STAFF' if instance.is_staff else 'CUSTOMER')
        UserProfile.objects.get_or_create(user=instance, defaults={'role': role, 'phone': ''})
