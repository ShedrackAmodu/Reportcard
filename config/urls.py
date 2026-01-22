
from django.contrib import admin
from django.urls import path, include

from schools.views import landing_view, manifest_view, sw_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path('manifest.json', manifest_view, name='manifest'),
    path('sw.js', sw_view, name='sw'),
    path("", landing_view, name='landing'),
    path("", include("schools.urls")),
]
