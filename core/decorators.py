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
                return redirect('login')
            
            # Check if user has profile
            if not hasattr(request.user, 'profile'):
                messages.error(request, 'User profile not found.')
                return redirect('home')
            
            # Check if user is blocked
            if request.user.profile.is_blocked:
                messages.error(request, 'Your account has been blocked. Contact admin.')
                return redirect('home')
            
            # Check role
            user_role = request.user.profile.role
            if user_role not in allowed_roles:
                messages.error(request, f'Access denied. This page is only for {", ".join(allowed_roles)}.')
                return redirect('home')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def log_action(action, model_name='', object_id=None, details=''):
    """
    Decorator to log actions to AuditLog.
    Usage: @log_action('Shop Approved', 'Shop', shop.id)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from orders.models import AuditLog
            
            # Execute the view
            response = view_func(request, *args, **kwargs)
            
            # Log the action
            if request.user.is_authenticated:
                ip = get_client_ip(request)
                AuditLog.objects.create(
                    user=request.user,
                    action=action,
                    model_name=model_name,
                    object_id=object_id,
                    details=details,
                    ip_address=ip
                )
            
            return response
        
        return wrapper
    return decorator


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
