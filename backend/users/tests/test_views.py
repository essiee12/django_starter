from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from users.tests.factories import UserFactory, UserOtpFactory
from users.views import CustomSocialLoginView, UserViewSet


class UserAuthViewsTests(APITestCase):
    def test_login_returns_tokens_for_verified_user(self):
        password = "strong-pass-123"
        user = UserFactory.create(password=password, is_email_verified=True)

        response = self.client.post(
            reverse("v1:user_login"),
            {"email": user.email, "password": password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["email"], user.email)

    @patch("users.views.send_otp_to_user_mail.apply_async")
    def test_login_triggers_otp_for_unverified_user(self, mock_apply_async):
        password = "strong-pass-123"
        user = UserFactory.create(password=password, is_email_verified=False)

        response = self.client.post(
            reverse("v1:user_login"),
            {"email": user.email, "password": password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("access", response.data)
        mock_apply_async.assert_called_once()

    def test_user_details_endpoint_returns_profile(self):
        user = UserFactory.create(is_email_verified=True)
        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("v1:user-user-details"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], user.email)

    def test_login_rejects_inactive_user(self):
        password = "strong-pass-123"
        user = UserFactory.create(
            password=password, is_email_verified=True, is_active=False
        )

        response = self.client.post(
            reverse("v1:user_login"),
            {"email": user.email, "password": password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("details", response.data)

    def test_refresh_token_success(self):
        user = UserFactory.create(is_email_verified=True)
        refresh = RefreshToken.for_user(user)

        response = self.client.post(
            reverse("v1:token_refresh"),
            {"refresh": str(refresh)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data["token"])

    def test_refresh_token_invalid(self):
        response = self.client.post(
            reverse("v1:token_refresh"),
            {"refresh": "invalid"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("users.serializers.send_otp_to_user_mail.apply_async")
    def test_otp_request_endpoint(self, mock_apply_async):
        user = UserFactory.create()

        response = self.client.post(
            reverse("v1:user-otp-request"),
            {"email": user.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_apply_async.assert_called_once()

    def test_otp_verification_endpoint_marks_user_verified(self):
        user = UserFactory.create(is_email_verified=False)
        UserOtpFactory.create(email=user.email, otp="123456")

        response = self.client.post(
            reverse("v1:user-otp-verification"),
            {"email": user.email, "otp": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        self.assertIn("access", response.data)

    def test_password_change_endpoint(self):
        user = UserFactory.create(password="oldpass123", is_email_verified=True)
        self.client.force_authenticate(user=user)

        response = self.client.post(
            reverse("v1:user-password-change"),
            {"password": "newpass456", "opassword": "oldpass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password("newpass456"))

    def test_forgot_password_endpoint(self):
        user = UserFactory.create(password="oldpass123", is_email_verified=True)
        self.client.force_authenticate(user=user)

        response = self.client.post(
            reverse("v1:user-forgot-password"),
            {"password": "freshpass789", "cpassword": "freshpass789"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password("freshpass789"))

    def test_logout_endpoint_blacklists_token(self):
        user = UserFactory.create(is_email_verified=True)
        self.client.force_authenticate(user=user)
        refresh = RefreshToken.for_user(user)

        response = self.client.post(
            reverse("v1:user-logout"),
            {"refresh": str(refresh)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            BlacklistedToken.objects.filter(token__token=str(refresh)).exists()
        )

    @patch("users.views.LoginView.post", side_effect=AssertionError)
    def test_custom_social_login_handles_assertion(self, mock_post):
        response = self.client.post(reverse("socialaccount_signup"), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("details", response.data)


class CustomSocialLoginViewTests(APITestCase):
    def test_get_response_returns_tokens(self):
        user = UserFactory.create(is_email_verified=True)
        request = APIRequestFactory().post(reverse("socialaccount_signup"))

        view = CustomSocialLoginView()
        view.request = request
        view.user = user

        response = view.get_response()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["email"], user.email)

    @patch("users.views.get_adapter")
    def test_process_login_calls_adapter(self, mock_get_adapter):
        request = APIRequestFactory().post(reverse("socialaccount_signup"))
        view = CustomSocialLoginView()
        view.request = request
        view.user = UserFactory.create(is_email_verified=True)

        view.process_login()

        mock_get_adapter.assert_called_once_with(request)


class UserViewSetPermissionsTests(APITestCase):
    def test_get_permissions_for_create_allows_any(self):
        view = UserViewSet()
        view.action = "create"
        permissions = view.get_permissions()
        self.assertTrue(any(isinstance(p, AllowAny) for p in permissions))

    def test_get_permissions_for_authenticated_action(self):
        view = UserViewSet()
        view.action = "user_details"
        permissions = view.get_permissions()
        self.assertTrue(any(isinstance(p, IsAuthenticated) for p in permissions))
