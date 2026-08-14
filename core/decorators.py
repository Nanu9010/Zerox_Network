from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*allowed_roles):
    """
    Decorator to restrict views by user role.
    Usage: @role_required('CUSTOMER') or @role_required('SHOP', 'ADMIN')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if user is authenticated
            if not request.user.is_authenticated:
                messages.error(request, 'Please login to access this page.')
                return redirect('core:login')
            
            # Check if user has profile
            if not hasattr(request.user, 'profile'):
                messages.error(request, 'User profile not found.')
                return redirect('core:home')
            
            # Check if user is blocked
            if request.user.profile.is_blocked:
                messages.error(request, 'Your account has been blocked. Contact admin.')
                return redirect('core:home')
            
            # Check role
            user_role = request.user.profile.role
            if user_role not in allowed_roles:
                messages.error(request, f'Access denied. This page is only for {", ".join(allowed_roles)}.')
                return redirect('core:home')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator
