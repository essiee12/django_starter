from django.contrib.auth import get_user_model

from users.models import UserOtp


class UserFactory:
    """Factory helpers for the custom User model."""

    counter = 0

    @classmethod
    def create(cls, **overrides):
        cls.counter += 1
        User = get_user_model()
        defaults = {
            "email": overrides.pop("email", f"user{cls.counter}@example.com"),
            "password": overrides.pop("password", "password123"),
            "full_name": overrides.pop("full_name", f"User {cls.counter}"),
        }
        password = defaults.pop("password")
        user = User.objects.create(**{**defaults, **overrides})
        user.set_password(password)
        if overrides.get("is_email_verified"):
            user.is_email_verified = True
        user.save()
        return user

    @classmethod
    def create_superuser(cls, **overrides):
        cls.counter += 1
        User = get_user_model()
        email = overrides.pop("email", f"admin{cls.counter}@example.com")
        password = overrides.pop("password", "adminpass123")
        return User.objects.create_superuser(
            email=email, password=password, **overrides
        )


class UserOtpFactory:
    counter = 0

    @classmethod
    def create(cls, **overrides):
        cls.counter += 1
        defaults = {
            "email": overrides.pop("email", f"user{cls.counter}@example.com"),
            "otp": overrides.pop("otp", "123456"),
        }
        return UserOtp.objects.create(**{**defaults, **overrides})
