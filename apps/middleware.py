"""
Middleware classes have been moved to authentication app.
Import from authentication.middleware instead.

Example:
    from authentication.middleware import MultiTenantMiddleware, AuthenticationRedirectMiddleware
"""

# For backward compatibility, import from the new location
from authentication.middleware import (
    MultiTenantMiddleware,
    AuthenticationRedirectMiddleware,
)

__all__ = [
    'MultiTenantMiddleware',
    'AuthenticationRedirectMiddleware',
]
