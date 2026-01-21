def school_context(request):
    from .models import School
    context = {'school': getattr(request, 'school', None)}

    # Add schools list for super admin navbar dropdown
    if request.user.is_authenticated and request.user.role == 'super_admin':
        context['schools'] = School.objects.all()

    return context
