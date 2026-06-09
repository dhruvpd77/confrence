from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def superuser_required(user):
    return user.is_authenticated and user.is_superuser


def faculty_required(user):
    return (
        user.is_authenticated
        and hasattr(user, 'faculty_profile')
        and not user.is_superuser
        and not hasattr(user, 'verifier_profile')
    )


def verifier_required(user):
    return (
        user.is_authenticated
        and hasattr(user, 'verifier_profile')
        and not user.is_superuser
    )


def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if verifier_required(request.user):
            return redirect('verifier_dashboard')
        if faculty_required(request.user):
            return redirect('faculty_dashboard')
        if not superuser_required(request.user):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def faculty_login_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return redirect('dashboard')
        if verifier_required(request.user):
            return redirect('verifier_dashboard')
        if not faculty_required(request.user):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def verifier_login_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return redirect('dashboard')
        if faculty_required(request.user):
            return redirect('faculty_dashboard')
        if not verifier_required(request.user):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper
