def school_context(request):
    from .models import School, UserApplication
    context = {'school': getattr(request, 'school', None)}

    # Add schools list for super admin navbar dropdown
    if request.user.is_authenticated and request.user.role == 'super_admin':
        context['schools'] = School.objects.all()

    # Add pending applications count for admins
    if request.user.is_authenticated and request.user.role in ['super_admin', 'admin']:
        if request.user.role == 'super_admin':
            # Super admin can see admin applications globally and teacher applications for all schools
            context['pending_applications_count'] = UserApplication.objects.filter(
                status='pending',
                role__in=['admin', 'teacher']
            ).count()
        elif request.user.role == 'admin':
            # School admin can only see teacher applications for their school
            context['pending_applications_count'] = UserApplication.objects.filter(
                status='pending',
                role='teacher',
                school=request.user.school
            ).count()

    return context
