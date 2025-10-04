import requests
from django.core.files.base import ContentFile
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from shortuuid.django_fields import ShortUUIDField

from .managers import CustomUserManager


class User(AbstractBaseUser, PermissionsMixin):
    idx = ShortUUIDField(primary_key=True, editable=False)
    full_name = models.CharField(blank=True, max_length=200)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to="profile-pictures/", blank=True, null=True
    )
    email = models.EmailField(_("email address"), unique=True)
    is_active = models.BooleanField(
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. Unselect this instead of deleting accounts."
        ),
    )
    is_staff = models.BooleanField(
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )

    is_email_verified = models.BooleanField(
        default=False,
        help_text=_("Designates whether the user has verified their email address."),
    )
    has_temp_password = models.BooleanField(
        default=False,
        help_text=_(
            "Designates whether the user has a temporary password set. This is used to enforce password changes on first login."
        ),
    )
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    @staticmethod
    def set_photo_from_url(user_instance, photo_url):
        """Save photo to the user profile"""
        response = requests.get(photo_url, timeout=10)
        if response.status_code == 200:
            user_instance.profile_picture.save(
                f"{user_instance.idx}.jpg", ContentFile(response.content), save=True
            )

    def __str__(self):
        return self.full_name or self.email


class UserOtp(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OTP for {self.email}"

    class Meta:
        verbose_name = "User OTP"
        verbose_name_plural = "User OTPs"
        ordering = ["-created_at"]
