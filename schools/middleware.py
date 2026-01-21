from django.utils.deprecation import MiddlewareMixin

from .models import School


class MultiTenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        school_id = request.headers.get('School-ID')
        if school_id:
            try:
                request.school = School.objects.get(id=school_id)
            except School.DoesNotExist:
                request.school = None
        else:
            # Check session for school_id (for web interface)
            session_school_id = request.session.get('school_id')
            if session_school_id:
                try:
                    request.school = School.objects.get(id=session_school_id)
                except School.DoesNotExist:
                    request.school = None
            else:
                request.school = None
