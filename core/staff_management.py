from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from core.decorators import role_required
from core.models import UserProfile
from orders.models import AuditLog

@role_required('ADMIN')
def add_staff(request):
    """Create new staff/admin accounts"""
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        full_name = request.POST.get('full_name')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        role = request.POST.get('role', 'STAFF')
        
        # Validation
        if password != password2:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'admin_portal/add_staff.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken!')
            return render(request, 'admin_portal/add_staff.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return render(request, 'admin_portal/add_staff.html')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=full_name
        )
        
        # Create profile with admin/staff role
        UserProfile.objects.create(
            user=user,
            role=role,
            phone=phone
        )
        
        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action='STAFF_CREATED',
            model_name='User',
            object_id=user.id,
            details=f'Created {role} account for {username}'
        )
        
        messages.success(request, f'✅ Staff account "{username}" created successfully!')
        return redirect('admin_portal:users')
    
    return render(request, 'admin_portal/add_staff.html')


@role_required('ADMIN')
def change_user_role(request, user_id):
    """Change user role (promote to admin/staff or demote)"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        new_role = request.POST.get('role')
        
        if new_role in ['CUSTOMER', 'SHOP', 'STAFF', 'ADMIN']:
            old_role = user.profile.role
            user.profile.role = new_role
            user.profile.save()
            
            # Audit log
            AuditLog.objects.create(
                user=request.user,
                action='ROLE_CHANGED',
                model_name='User',
                object_id=user.id,
                details=f'Changed {user.username} role from {old_role} to {new_role}'
            )
            
            messages.success(request, f'✅ User role updated to {new_role}')
        else:
            messages.error(request, 'Invalid role selected!')
    
    return redirect('admin_portal:users')
