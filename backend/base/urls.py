from django.urls import path
from . import views

urlpatterns = [
    path("ping", views.ping_view, name="ping"),
    path("iconfig", views.settings_view, name="iconfig"),
]
