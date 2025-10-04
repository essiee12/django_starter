from django.urls import path, include

v1_urlpatterns = [
    path("", include("users.urls")),
]
