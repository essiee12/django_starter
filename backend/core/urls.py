"""
Base urls
"""

from rest_framework import permissions
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from users.views import GoogleLoginView
from .custom_urls import v1_urlpatterns
from .ckeditor_upload import upload_file


schema_view = get_schema_view(
    openapi.Info(
        title="Django",
        default_version="v1",
        description="Django Api Documentation",
        terms_of_service="#",
        contact=openapi.Contact(email="contact@django.com"),
        license=openapi.License(name="Django"),
    ),
    public=True,
    permission_classes=(permissions.IsAuthenticated,),
)


urlpatterns = [
    path("", include("base.urls")),
    path(settings.ADMIN_URL + "/", admin.site.urls),
    path("ckeditor5/image_upload/", upload_file, name="ck_editor_5_upload_file"),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
]


urlpatterns += [
    path("api/v1/", include((v1_urlpatterns, "v1"))),
    # Google OAuth2 login/signup
    path(
        "api/v1/google-login/", GoogleLoginView.as_view(), name="socialaccount_signup"
    ),
]

urlpatterns += [
    path(
        "swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"
    ),
    path(
        "api/v1/docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path("__debug__", include(debug_toolbar.urls))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Django Admin"
admin.site.site_title = "Django Admin Dashboard"
admin.site.index_title = "Django Admin Dashboard"
