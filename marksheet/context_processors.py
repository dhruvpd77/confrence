def portal_roles(request):
    if not request.user.is_authenticated:
        return {
            'is_admin': False,
            'is_faculty': False,
            'is_verifier': False,
        }
    is_admin = request.user.is_superuser
    is_verifier = hasattr(request.user, 'verifier_profile') and not is_admin
    is_faculty = hasattr(request.user, 'faculty_profile') and not is_admin and not is_verifier
    return {
        'is_admin': is_admin,
        'is_faculty': is_faculty,
        'is_verifier': is_verifier,
    }
