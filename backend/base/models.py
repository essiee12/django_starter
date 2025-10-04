from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from shortuuid.django_fields import ShortUUIDField


User = get_user_model()


class TimeAuditModel(models.Model):
    """Time Audit model"""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class UserAuditModel(models.Model):
    """User audit model"""

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_created_by",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_updated_by",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class BaseUserModel(TimeAuditModel, UserAuditModel):
    """Base User model mixin"""

    idx = ShortUUIDField(primary_key=True, editable=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now() # pragma: no cover
        super().save(*args, **kwargs) # pragma: no cover


class BaseModel(TimeAuditModel):
    """Base model"""

    idx = ShortUUIDField(primary_key=True, editable=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class Config(BaseModel):
    """
    This is used to store configuration values. This just stores a key value pair
    """

    name = models.CharField(max_length=100)
    enabled = models.BooleanField(default=True)
    slug = models.SlugField(max_length=100, unique=True)
    value = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
