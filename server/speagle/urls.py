from django.conf.urls import url, include
from rest_framework import routers
from .views import UserViewSet


router = routers.DefaultRouter()
# DefaultRouter class will define the standard REST endpoints.
router.register(r'users', UserViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]