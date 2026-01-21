
from django.contrib import admin
from django.urls import path, include

from schools.views import landing_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", landing_view, name='landing'),
    path("", include("schools.urls")),
]
