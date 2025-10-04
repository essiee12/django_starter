from allauth.account.adapter import get_adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from django.utils.translation import gettext_lazy as _
from dj_rest_auth.views import LoginView
from rest_framework import status, generics
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from base.views import BaseModelViewSet
from .models import User
from .serializers import (
    UserLoginSerializer,
    UserRefreshTokenSerializer,
    PasswordChangeSerializer,
    UserLogoutSerializer,
    UserSerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
    ForgotPasswordSerializer,
    SocialLoginInputSerializer,
)
from .tasks import send_otp_to_user_mail


class CustomSocialLoginView(LoginView):
    """
    Custom view for handling social logins.
    """

    serializer_class = SocialLoginInputSerializer

    def get_response(self):
        """
        Override the default response data for social logins.
        """
        user = self.user
        refresh = RefreshToken.for_user(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            **UserSerializer(user, context={"request": self.request}).data,
        }

        return Response(data=data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for social logins.
        """
        try:
            response = super().post(request, *args, **kwargs)
            return response

        except AssertionError:
            return Response(
                {
                    "details": _(
                        "Email address is already associated with an existing account."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def process_login(self):
        get_adapter(self.request).login(self.request, self.user)


class GoogleLoginView(CustomSocialLoginView):
    """
    Google OAuth2 signup
    Format: {"access_token":authCode}
    """

    adapter_class = GoogleOAuth2Adapter
    permission_classes = [AllowAny]


class UserLoginView(generics.GenericAPIView):
    """Login user using email and password"""

    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0]) from e
        user = serializer.user

        if not user.is_active:
            return Response(
                {"details": "Account is currently inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_data = serializer.validated_data

        if not user.is_email_verified:
            send_otp_to_user_mail.apply_async(args=[user.email], countdown=2)
            return Response(
                UserSerializer(user, context={"request": self.request}).data
            )

        response_data.update(
            **UserSerializer(user, context={"request": self.request}).data
        )
        return Response(response_data, status=status.HTTP_200_OK)


class UserRefreshTokenView(generics.GenericAPIView):
    """View for user refresh token"""

    serializer_class = UserRefreshTokenSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            return Response({"details": e.args[0]}, status=status.HTTP_401_UNAUTHORIZED)
        response_context = serializer.validated_data
        return Response({"token": response_context}, status=status.HTTP_200_OK)


class UserViewSet(BaseModelViewSet):
    """
    A viewset for viewing and editing user instance.
    """

    http_method_names = ["get", "post", "patch"]
    pagination_class = None
    ordering_fields = ["date_joined"]

    def get_permissions(self):
        if self.action in ["create", "otp_request", "otp_verification"]:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        """Serializer based on action"""
        if self.action == "logout":
            return UserLogoutSerializer
        if self.action == "otp_request":
            return OtpRequestSerializer
        if self.action == "otp_verification":
            return OtpVerifySerializer
        if self.action == "password_change":
            return PasswordChangeSerializer
        if self.action == "forgot_password":
            return ForgotPasswordSerializer
        return UserSerializer

    def get_queryset(self):
        """Return current user only"""
        return User.objects.filter(idx=self.request.user.idx)

    @action(detail=False, methods=["get"], url_path="details")
    def user_details(self, request):
        """
        This endpoint retrieves the details of the currently authenticated user.
        """
        user = self.get_queryset().get(idx=request.user.idx)
        serializer = UserSerializer(user, context={"request": self.request})
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="otp-request")
    def otp_request(self, request):
        """
        This endpoint allows users to request an OTP to be sent to their email address.
        Example request body:
        {
            "email": "user@example.com"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"details": "Otp Sent successfully."})

    @action(detail=False, methods=["post"], url_path="otp-verification")
    def otp_verification(self, request):
        """
        This endpoint verifies the OTP sent to the user's email address.
        Example request body:
        {
            "email": "user@example.com",
            "otp": "123456"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.save()
        user = User.objects.get(email=email)
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
        refresh = RefreshToken.for_user(user)
        response_context = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            **UserSerializer(user, context={"request": request}).data,
        }
        return Response(response_context, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="password-change")
    def password_change(self, request):
        """Change the password of current user."""
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"details": "Password changed successfully."})

    @action(detail=False, methods=["post"], url_path="forgot-password")
    def forgot_password(self, request):
        """Change the password of current user without previous password."""
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"details": "Password changed successfully."})

    @action(detail=False, methods=["post"])
    def logout(self, request):
        """Blacklist current token."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"details": "Logout successfully."})
