"""
Middleware classes have been moved to authentication app.
Import from authentication.middleware instead.

Example:
    from authentication.middleware import MultiTenantMiddleware, AuthenticationRedirectMiddleware
"""

# For backward compatibility, import from the new location
try:
    # Import the currently available middleware from the authentication app
    from authentication.middleware import MultiTenantMiddleware
except Exception:
    # Fallback stub to avoid import errors for older code that imports apps.middleware
    class MultiTenantMiddleware:
        def __init__(self, *args, **kwargs):
            raise ImportError('MultiTenantMiddleware is not available. Ensure `authentication.middleware` exists.')

__all__ = [
    'MultiTenantMiddleware',
]
