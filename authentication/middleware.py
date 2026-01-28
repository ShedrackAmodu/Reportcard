"""
Custom middleware for multi-tenant support and authentication redirection.
"""

from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from apps.models import School


class MultiTenantMiddleware(MiddlewareMixin):
    """
    Middleware to handle multi-tenant architecture.
    Sets the current school context from headers or session.
    """
    
    def process_request(self, request):
        """
        Process request to set school context.
        Priority: Header > Session > None
        """
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
    Middleware to redirect unauthenticated users to landing page
    instead of Django's default login page.
    """
    
    # Paths that should not be redirected
    SKIP_PATHS = [
        '/login/',
        '/accounts/login/',
        '/auth/login/',
        '/schools/school_create/',
        '/schools/school_update/',
        '/schools/school_delete/',
    ]
    
    # Form submission paths that should not redirect
    FORM_PATHS = [
        '/login/',
        '/accounts/login/',
        '/auth/login/',
    ]
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Process view to redirect unauthenticated users.
        """
        # Skip middleware for API endpoints
        if request.path.startswith('/api/'):
            return None
            
        # Skip middleware for static files and media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None
            
        # Skip middleware for manifest.json and sw.js
        if request.path in ['/manifest.json', '/sw.js']:
            return None
        
        current_path = request.path
        
        # Check if the current path should be skipped
        if any(current_path.startswith(path) for path in self.SKIP_PATHS):
            return None
            
        # Allow unauthenticated access to landing and offline pages
        if current_path in ['/', '/landing/', '/offline/']:
            return None
            
        # Skip middleware for logout view to prevent redirect loops
        if current_path.startswith('/accounts/logout/'):
            return None
            
        # Skip form submissions
        if request.method == 'POST' and any(current_path.startswith(path) for path in self.FORM_PATHS):
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
