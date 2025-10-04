from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core.management.commands import diffsettings
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny, IsAuthenticated


@never_cache
def ping_view(request):
    """Ping the server"""
    return HttpResponse("pong")


@never_cache
@user_passes_test(lambda u: u.is_superuser, login_url=f"{settings.ADMIN_URL}/")
def settings_view(request):
    """View all settings"""
    output = diffsettings.Command().handle(default=None, output="hash", all=False)
    desensitized = []
    for line in output.splitlines():
        if "SECRET" in line or "KEY" in line:
            continue
        desensitized.append(line)
    return HttpResponse("<br/>".join(desensitized))


class BaseModelViewSet(viewsets.ModelViewSet):
    """Base viewset for all authenticated apis"""

    queryset = None
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    ordering_fields = ["created_at", "updated_at"]


class BasePublicModelViewSet(viewsets.ReadOnlyModelViewSet):
    """Base viewset for all public apis"""

    queryset = None
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
