
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.urls import re_path

from apps.views import landing_view, manifest_view, sw_view, offline_view

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # Authentication app (accessible as /auth/ and /accounts/ for compatibility)
    path("auth/", include("authentication.urls", namespace="auth")),
    path("accounts/", include("authentication.urls", namespace="accounts")),
    
    # PWA files
    path('manifest.json', manifest_view, name='manifest'),
    path('sw.js', sw_view, name='sw'),
    path('offline/', offline_view, name='offline'),
    
    # Landing page
    path("", landing_view, name='landing'),
    
    # App URLs (schools, users, etc.)
    path("", include("apps.urls")),
]

# Serve static files directly at root level for PWA files
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^manifest\.json$', serve, {'document_root': settings.BASE_DIR, 'path': 'static/manifest.json'}),
        re_path(r'^sw\.js$', serve, {'document_root': settings.BASE_DIR, 'path': 'static/sw.js'}),
    ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
