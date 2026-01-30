from django.utils.deprecation import MiddlewareMixin


class MultiTenantMiddleware(MiddlewareMixin):
    """Attach `request.school` for convenience based on authenticated user."""
    def process_request(self, request):
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            request.school = getattr(user, 'school', None)
        else:
            request.school = None


class AuthenticationRedirectMiddleware(MiddlewareMixin):
    """Placeholder middleware for auth-related redirects. Currently no-op."""
    def process_request(self, request):
        return None


class NoCacheMiddleware(MiddlewareMixin):
    """
    Add no-cache headers to all responses for authenticated pages.
    This prevents browsers from caching pages with user-specific content.
    """
    def process_response(self, request, response):
        user = getattr(request, 'user', None)
        
        # Check if user is authenticated
        if user and getattr(user, 'is_authenticated', False):
            # Add no-cache headers for authenticated users
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response

