from rest_framework import routers
from django.urls import path, include

router = routers.DefaultRouter()
# register viewsets when implemented, e.g.:
# from apps.schools.views import SchoolViewSet
# router.register(r"schools", SchoolViewSet, basename="school")

urlpatterns = [
    path("api/", include(router.urls)),
]