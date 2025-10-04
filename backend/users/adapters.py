from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied

from .models import User


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Perform pre-login actions before connecting a social account to a user.
        """

        if not sociallogin.user.is_active:
            raise PermissionDenied(
                _("Your account has been banned. Please contact support for details!")
            )

        user = request.user

        s_email = sociallogin.account.extra_data.get("email", None)

        if not s_email:
            raise PermissionDenied(
                _("The social account does not provide an email address.")
            )

        if user.is_authenticated:
            social_account_uid = sociallogin.account.uid
            # Social provider (e.g., Google, Facebook)
            social_account_provider = sociallogin.account.provider
            # Check if social account already exists for provided uid and provider
            if (
                SocialAccount.objects.filter(
                    uid=social_account_uid,
                    provider__iexact=social_account_provider,
                )
                .exclude(user=user)
                .exists()
            ):
                raise AssertionError
            # Check if a user already exists with the provided email if it does raise error.
            try:
                if User.objects.get(email=s_email):
                    raise AssertionError
            except (User.DoesNotExist, ValueError):
                # if user with social email does not exist connect it with current user.
                sociallogin.connect(request, user)

    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login. In case of auto-signup,
        the signup form is not available.
        """
        name = sociallogin.account.extra_data.get("name", None)
        email = sociallogin.account.extra_data.get("email", None)
        profile_pic = sociallogin.account.extra_data.get("picture", None)

        new_user = sociallogin.user
        new_user.full_name = name
        new_user.email = email
        new_user.is_email_verified = True
        new_user.set_unusable_password()

        if not new_user.pk:
            new_user.save()

        User.set_photo_from_url(new_user, profile_pic)
        sociallogin.save(request)
        return new_user
