from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import User


class UserAdmin(BaseUserAdmin):
    list_display = [
        "avatar",
        "email",
        "full_name",
        "is_active",
        "date_joined",
        "last_login",
    ]
    list_display_links = ["avatar", "email", "full_name"]
    search_fields = ["email", "full_name", "phone_number"]
    list_filter = ["is_active", "is_staff", "is_superuser", "is_email_verified"]
    search_help_text = "Search by full name, email"
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    model = User

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "full_name",
                    "email",
                    "profile_picture",
                    "phone_number",
                    "password",
                    "is_email_verified",
                    "has_temp_password",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "user_permissions",
                    "groups",
                )
            },
        ),
        (
            "Important dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("full_name", "email", "password1", "password2", "is_active"),
            },
        ),
    )

    def image_tag(self, img_url=None):
        """
        Returns an HTML image tag for the user's profile picture.
        """
        default_style = "width: 50px; height: 50px; border-radius: 50%;"
        if not img_url:
            img_url = "/static/images/default-user-avatar.png"
            default_style += "filter: invert(60%);"
        return format_html('<img src="{}" style="{}">'.format(img_url, default_style))

    def avatar(self, obj):
        return (
            self.image_tag(obj.profile_picture.url)
            if obj.profile_picture
            else self.image_tag()
        )

    ordering = ("date_joined",)
    list_per_page = 20


admin.site.register(User, UserAdmin)
