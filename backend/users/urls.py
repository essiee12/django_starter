from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import (
    UserLoginView,
    UserViewSet,
    UserRefreshTokenView,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("users/login/", UserLoginView.as_view(), name="user_login"),
    path("", include(router.urls)),
    path("users/token/refresh/", UserRefreshTokenView.as_view(), name="token_refresh"),
]
