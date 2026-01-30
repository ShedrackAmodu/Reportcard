
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.urls import re_path


urlpatterns = [
    path("admin/", admin.site.urls),
    
    # Authentication app
    path("auth/", include("authentication.urls", namespace="auth")),
    # Legacy/account-compatible routes
    path("accounts/", include("authentication.urls", namespace="auth")),
    
    # App URLs (includes landing and PWA endpoints)
    path("", include("apps.urls")),
]

# Serve static files directly at root level for PWA files
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^manifest\.json$', serve, {'document_root': settings.BASE_DIR, 'path': 'static/manifest.json'}),
        re_path(r'^sw\.js$', serve, {'document_root': settings.BASE_DIR, 'path': 'static/sw.js'}),
    ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
