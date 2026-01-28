from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required

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


class AuthenticationRedirectMiddleware(MiddlewareMixin):
    """
    Middleware to redirect unauthenticated users trying to access protected views
    to the landing page instead of the login page.
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip middleware for API endpoints
        if request.path.startswith('/api/'):
            return None
            
        # Skip middleware for static files and media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None
            
        # Skip middleware for manifest.json and sw.js
        if request.path in ['/manifest.json', '/sw.js']:
            return None
            
        # Skip middleware for specific endpoints that should not redirect
        # Only skip specific endpoints, not all POST requests to /schools/
        skip_paths = [
            '/login/',
            '/accounts/login/',
            '/auth/login/',
            '/schools/school_create/',
            '/schools/school_update/',
            '/schools/school_delete/',
        ]
        
        # Check if the current path should be skipped
        current_path = request.path
        if any(current_path.startswith(path) for path in skip_paths):
            return None
            
        # Skip middleware for the landing page itself - allow unauthenticated access
        if current_path == '/' or current_path == '/landing/':
            return None
            
        # Skip middleware for logout view to prevent redirect loops
        if current_path.startswith('/accounts/logout/'):
            return None
            
        # Skip middleware for form submission endpoints that need CSRF protection
        # Only skip specific form endpoints, not all POST requests
        form_paths = [
            '/login/',
            '/accounts/login/',
            '/auth/login/',
        ]
        
        if request.method == 'POST' and any(current_path.startswith(path) for path in form_paths):
            return None
            
        # Check if the view is protected by @login_required decorator
        if hasattr(view_func, 'view_class'):
            # For class-based views, check if they have login_required
            view_class = view_func.view_class
            if hasattr(view_class, 'dispatch'):
                # Check if any method in the class has login_required
                for method_name in ['get', 'post', 'put', 'delete', 'patch']:
                    if hasattr(view_class, method_name):
                        method = getattr(view_class, method_name)
                        if hasattr(method, '_is_login_required'):
                            if not request.user.is_authenticated:
                                return redirect('landing')
        else:
            # For function-based views, check if they have login_required decorator
            if hasattr(view_func, '_is_login_required'):
                if not request.user.is_authenticated:
                    return redirect('landing')
        
        return None
