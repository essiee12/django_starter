from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponseBadRequest
from django.urls.exceptions import NoReverseMatch
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.reverse import reverse
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from requests.exceptions import HTTPError

from allauth.socialaccount.models import SocialApp
from allauth.account import app_settings as allauth_account_settings
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.providers.oauth2.client import OAuth2Error

from users.models import User, UserOtp
from users.tasks import send_otp_to_user_mail


class UserLoginSerializer(TokenObtainPairSerializer):
    """Serializer used for user login"""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        return data


class UserRefreshTokenSerializer(TokenRefreshSerializer):
    """Serializer used for user refresh token"""

    refresh = serializers.CharField()


class OtpRequestSerializer(serializers.Serializer):
    """Serializer used for otp request"""

    email = serializers.CharField(max_length=150)

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value

    def save(self):
        email = self.validated_data["email"].lower()
        send_otp_to_user_mail.apply_async(args=[email], countdown=5)
        return email


class OtpVerifySerializer(serializers.Serializer):
    """Serializer used for otp verification"""

    email = serializers.CharField(max_length=150)
    otp = serializers.CharField(max_length=6, min_length=6)

    def validate_otp(self, value):
        """
        Validate that the OTP is exactly 6 digits in length.
        """
        if len(str(value)) != 6:
            raise serializers.ValidationError("OTP must be exactly 6 digits.")
        return value

    def validate(self, attrs):
        data = super().validate(attrs)
        otp = str(data["otp"])
        email = data["email"].lower()
        user_otp = None
        try:
            user_otp = UserOtp.objects.get(email=email)
        except UserOtp.DoesNotExist as exc:
            raise serializers.ValidationError(
                {
                    "email": _(
                        "Otp is expired or email is incorrect. Please retry again."
                    )
                }
            ) from exc
        stored_otp = str(user_otp.otp) if user_otp else None
        if stored_otp is None or stored_otp != otp:
            raise serializers.ValidationError(
                {"otp": _("Otp is expired or not matched.")}
            )
        return data

    def save(self):
        return self.validated_data["email"].lower()


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer used for password change"""

    password = serializers.CharField(write_only=True, label=_("New Password"))
    opassword = serializers.CharField(write_only=True, label=_("Old Password"))

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.context["request"].user
        old_password = data.get("opassword")
        if not user.check_password(old_password):
            raise serializers.ValidationError(
                {"opassword": _("The old password you entered is incorrect.")}
            )

        new_password = data.get("password")
        if new_password == old_password:
            raise serializers.ValidationError(
                {
                    "password": _(
                        "The new password cannot be the same as the old password."
                    )
                }
            )
        return data

    def save(self):
        user = self.context["request"].user
        password = self.validated_data["password"]
        user.set_password(password)
        user.has_temp_password = False
        user.save()
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer used in the case of forgot password"""

    password = serializers.CharField(max_length=60)
    cpassword = serializers.CharField(max_length=60)

    def validate(self, attrs):
        data = super().validate(attrs)
        if data["password"] != data["cpassword"]:
            raise serializers.ValidationError({"password": _("Passwords do not match")})
        return data

    def save(self):
        user = self.context["request"].user
        password = self.validated_data["password"]
        user.set_password(password)
        user.has_temp_password = False
        user.save(update_fields=["password", "has_temp_password"])
        return user


class UserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(allow_null=True, required=False)
    password_based_auth = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "idx",
            "email",
            "full_name",
            "password",
            "profile_picture",
            "is_email_verified",
            "password_based_auth",
            "has_temp_password",
        ]

        extra_kwargs = {
            "password": {"write_only": True},
            "full_name": {"required": True},
            "is_email_verified": {"read_only": True},
            "has_temp_password": {"read_only": True},
        }

    def get_password_based_auth(self, obj):
        return obj.has_usable_password()

    def validate(self, attrs):
        data = super().validate(attrs)
        return data

    def create(self, validated_data):
        with transaction.atomic():
            password = validated_data.pop("password", None)
            user = User.objects.create(**validated_data)
            user.set_password(password)
            user.save()
            send_otp_to_user_mail.apply_async(args=[user.email], countdown=5)
            return user

    def update(self, instance, validated_data):
        email = validated_data.get("email", instance.email)
        password = validated_data.pop("password", None)
        if instance.email != email:
            instance.is_email_verified = False
            try:
                tokens = OutstandingToken.objects.filter(user=instance)
                for token in tokens:
                    try:
                        BlacklistedToken.objects.get_or_create(token=token)
                    except TokenError:
                        continue
            except Exception:
                pass

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class UserLogoutSerializer(serializers.Serializer):
    """Logout users token"""

    refresh = serializers.CharField()

    message = _("Token is expired or invalid.")

    def validate(self, attrs):
        token = attrs.get("refresh")
        try:
            token = RefreshToken(token)
            return token
        except Exception as exc:
            raise serializers.ValidationError({"refresh": self.message}) from exc

    def save(self, **kwargs):
        token = self.validated_data
        try:
            existing = BlacklistedToken.objects.filter(token__token=str(token)).first()
            if existing:
                return existing
            token.blacklist()
            return token
        except Exception as exc:
            raise serializers.ValidationError({"refresh": self.message}) from exc


class SocialLoginInputSerializer(serializers.Serializer):
    """Serializer for handling OAuth2 social logins without username field."""

    access_token = serializers.CharField(required=False, allow_blank=True)
    code = serializers.CharField(required=False, allow_blank=True)
    id_token = serializers.CharField(required=False, allow_blank=True)

    def _get_request(self):
        request = self.context.get("request")
        if isinstance(request, HttpRequest):
            return request
        return request._request

    def _get_adapter(self):
        view = self.context.get("view")
        if not view:
            raise serializers.ValidationError(
                _("View is not defined, pass it as a context variable"),
            )
        adapter_class = getattr(view, "adapter_class", None)
        if not adapter_class:
            raise serializers.ValidationError(_("Define adapter_class in view"))
        return adapter_class(self._get_request())

    def _build_callback_url(self, view, adapter_class):
        callback_url = getattr(view, "callback_url", None)
        if callback_url:
            return callback_url
        try:
            return reverse(
                viewname=f"{adapter_class.provider_id}_callback",
                request=self._get_request(),
            )
        except NoReverseMatch as exc:
            raise serializers.ValidationError(_("Define callback_url in view")) from exc

    def validate(self, attrs):
        view = self.context.get("view")
        adapter = self._get_adapter()

        try:
            provider = adapter.get_provider()
            app = provider.app
        except SocialApp.DoesNotExist as exc:
            raise serializers.ValidationError(
                _(
                    "Social application for '%(provider)s' is not configured. "
                    "Add a SocialApp entry in the Django admin and try again."
                )
                % {"provider": adapter.provider_id}
            ) from exc

        access_token = attrs.get("access_token")
        code = attrs.get("code")

        tokens_to_parse = {}
        token_payload = None

        if access_token:
            tokens_to_parse["access_token"] = access_token
            token_payload = access_token
            id_token = attrs.get("id_token")
            if id_token:
                tokens_to_parse["id_token"] = id_token
        elif code:
            client_class = getattr(view, "client_class", None)
            if not client_class:
                raise serializers.ValidationError(_("Define client_class in view"))

            callback_url = self._build_callback_url(view, adapter.__class__)
            scope = provider.get_scope(self._get_request())

            client = client_class(
                self._get_request(),
                app.client_id,
                app.secret,
                adapter.access_token_method,
                adapter.access_token_url,
                callback_url,
                scope,
                scope_delimiter=adapter.scope_delimiter,
                headers=adapter.headers,
                basic_auth=adapter.basic_auth,
            )

            try:
                token_response = client.get_access_token(code)
            except OAuth2Error as exc:
                raise serializers.ValidationError(
                    _("Failed to exchange code for access token")
                ) from exc

            access_token = token_response["access_token"]
            tokens_to_parse["access_token"] = access_token
            token_payload = token_response

            for key in ["refresh_token", "id_token", adapter.expires_in_key]:
                if key in token_response:
                    tokens_to_parse[key] = token_response[key]
        else:
            raise serializers.ValidationError(
                _("Incorrect input. access_token or code is required."),
            )

        social_token = adapter.parse_token(tokens_to_parse)
        social_token.app = app

        try:
            if adapter.provider_id == "google" and not code:
                login = adapter.complete_login(
                    self._get_request(),
                    app,
                    social_token,
                    response={"id_token": attrs.get("id_token")},
                )
            else:
                login = adapter.complete_login(
                    self._get_request(),
                    app,
                    social_token,
                    response=token_payload,
                )
            login.token = social_token
            result = complete_social_login(self._get_request(), login)
        except HTTPError as exc:
            raise serializers.ValidationError(_("Incorrect value")) from exc
        except NoReverseMatch as exc:
            raise serializers.ValidationError(
                _(
                    "Unable to resolve social signup route. Ensure allauth URLs "
                    "are included and auto-signup is enabled."
                )
            ) from exc

        if isinstance(result, HttpResponseBadRequest):
            raise serializers.ValidationError(result.content)

        if not login.is_existing:
            if allauth_account_settings.UNIQUE_EMAIL:
                email = login.user.email
                if email and get_user_model().objects.filter(email=email).exists():
                    raise serializers.ValidationError(
                        _("User is already registered with this e-mail address."),
                    )

            login.lookup()
            try:
                login.save(self._get_request(), connect=True)
            except IntegrityError as exc:
                raise serializers.ValidationError(
                    _("User is already registered with this e-mail address."),
                ) from exc

            self._post_signup(login, attrs)

        attrs["user"] = login.account.user
        return attrs

    def _post_signup(self, login, attrs):
        """Hook for additional signup steps."""
        pass
