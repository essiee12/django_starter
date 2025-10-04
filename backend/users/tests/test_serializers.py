from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError

from users.models import UserOtp
from users.serializers import (
    ForgotPasswordSerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
    PasswordChangeSerializer,
    UserLogoutSerializer,
    UserSerializer,
)
from users.tests.factories import UserFactory, UserOtpFactory


class OtpRequestSerializerTests(TestCase):
    def test_validate_email_passes_for_existing_user(self):
        user = UserFactory.create(email="exists@example.com")
        serializer = OtpRequestSerializer(data={"email": user.email})
        serializer.is_valid(raise_exception=True)
        self.assertEqual(serializer.validated_data["email"], user.email)

    def test_validate_email_raises_when_user_missing(self):
        serializer = OtpRequestSerializer(data={"email": "missing@example.com"})
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    @patch("users.serializers.send_otp_to_user_mail.apply_async")
    def test_save_dispatches_task(self, mock_apply_async):
        user = UserFactory.create(email="Test@Example.com")
        serializer = OtpRequestSerializer(data={"email": user.email})
        serializer.is_valid(raise_exception=True)

        returned_email = serializer.save()

        self.assertEqual(returned_email, user.email.lower())
        mock_apply_async.assert_called_once_with(args=[user.email.lower()], countdown=5)


class OtpVerifySerializerTests(TestCase):
    def test_verify_accepts_correct_otp(self):
        record = UserOtpFactory.create(email="otp@example.com", otp="123456")
        serializer = OtpVerifySerializer(data={"email": record.email, "otp": "123456"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.save(), record.email)

    def test_verify_rejects_invalid_code(self):
        UserOtpFactory.create(email="otp@example.com", otp="123456")
        serializer = OtpVerifySerializer(
            data={"email": "otp@example.com", "otp": "000000"}
        )
        self.assertFalse(serializer.is_valid())

    def test_verify_raises_when_otp_length_is_greater_than_six(self):
        serializer = OtpVerifySerializer(
            data={"email": "otp@example.com", "otp": "1234568"}
        )
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_verify_rejects_invalid_length(self):
        serializer = OtpVerifySerializer(
            data={"email": "otp@example.com", "otp": "123"}
        )
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_verify_raises_when_record_missing(self):
        serializer = OtpVerifySerializer(
            data={"email": "missing@example.com", "otp": "123456"}
        )
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)


class PasswordChangeSerializerTests(TestCase):
    def test_password_change_updates_user_credentials(self):
        user = UserFactory.create(password="oldpass123", is_email_verified=True)
        serializer = PasswordChangeSerializer(
            data={"password": "newpass456", "opassword": "oldpass123"},
            context={"request": MagicMock(user=user)},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        user.refresh_from_db()
        self.assertTrue(user.check_password("newpass456"))

    def test_password_change_rejects_wrong_old_password(self):
        user = UserFactory.create(password="oldpass123")
        serializer = PasswordChangeSerializer(
            data={"password": "newpass456", "opassword": "wrongpass"},
            context={"request": MagicMock(user=user)},
        )
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_password_change_rejects_same_password(self):
        user = UserFactory.create(password="samepass")
        serializer = PasswordChangeSerializer(
            data={"password": "samepass", "opassword": "samepass"},
            context={"request": MagicMock(user=user)},
        )
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)


class ForgotPasswordSerializerTests(TestCase):
    def test_forgot_password_sets_new_password(self):
        user = UserFactory.create(password="oldpass123", is_email_verified=True)
        serializer = ForgotPasswordSerializer(
            data={"password": "freshpass789", "cpassword": "freshpass789"},
            context={"request": MagicMock(user=user)},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        user.refresh_from_db()
        self.assertTrue(user.check_password("freshpass789"))

    def test_forgot_password_mismatch(self):
        user = UserFactory.create(password="oldpass123", is_email_verified=True)
        serializer = ForgotPasswordSerializer(
            data={"password": "freshpass789", "cpassword": "different"},
            context={"request": MagicMock(user=user)},
        )
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)


class UserSerializerTests(TestCase):
    @patch("users.serializers.send_otp_to_user_mail.apply_async")
    def test_create_user_triggers_otp_task(self, mock_apply_async):
        serializer = UserSerializer(
            data={
                "email": "new@example.com",
                "full_name": "New User",
                "password": "secretpass123",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.email, "new@example.com")
        mock_apply_async.assert_called_once()

    def test_update_user_flags_email_change(self):
        user = UserFactory.create(email="old@example.com", is_email_verified=True)
        serializer = UserSerializer(
            instance=user,
            data={"email": "new@example.com", "full_name": "Updated"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        user.refresh_from_db()
        self.assertFalse(user.is_email_verified)
        self.assertEqual(user.full_name, "Updated")

    @patch("users.serializers.BlacklistedToken.objects.get_or_create")
    @patch("users.serializers.OutstandingToken.objects.filter")
    def test_update_user_blacklists_outstanding_tokens(
        self, mock_filter, mock_get_or_create
    ):
        user = UserFactory.create(email="old@example.com", is_email_verified=True)
        mock_filter.return_value = [MagicMock(), MagicMock()]
        mock_get_or_create.side_effect = [TokenError("bad"), (MagicMock(), True)]

        serializer = UserSerializer(
            instance=user,
            data={"email": "new@example.com", "full_name": "Updated"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        mock_filter.assert_called_once()
        self.assertEqual(mock_get_or_create.call_count, 2)

    @patch(
        "users.serializers.OutstandingToken.objects.filter",
        side_effect=Exception("boom"),
    )
    def test_update_handles_outstanding_exception(self, mock_filter):
        user = UserFactory.create(email="old@example.com", is_email_verified=True)
        serializer = UserSerializer(
            instance=user, data={"email": "new@example.com"}, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        mock_filter.assert_called_once()

    def test_password_based_auth_field(self):
        user = UserFactory.create()
        serializer = UserSerializer(instance=user)
        self.assertTrue(serializer.data["password_based_auth"])

    def test_update_user_sets_password_when_provided(self):
        user = UserFactory.create(password="oldpass")
        serializer = UserSerializer(
            instance=user, data={"password": "newpass123"}, partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        user.refresh_from_db()
        self.assertTrue(user.check_password("newpass123"))


class UserLogoutSerializerTests(TestCase):
    @patch("users.serializers.RefreshToken")
    def test_logout_serializer_blacklists_token(self, mock_refresh):
        token_mock = MagicMock()
        mock_refresh.return_value = token_mock

        serializer = UserLogoutSerializer(data={"refresh": "token"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        token_mock.blacklist.assert_called_once()

    def test_logout_serializer_raises_on_invalid_token(self):
        serializer = UserLogoutSerializer(data={"refresh": "token"})
        with patch("users.serializers.RefreshToken", side_effect=Exception):
            self.assertFalse(serializer.is_valid())

    @patch("users.serializers.BlacklistedToken.objects.filter")
    @patch("users.serializers.RefreshToken")
    def test_logout_serializer_returns_existing_blacklisted(
        self, mock_refresh, mock_filter
    ):
        token_mock = MagicMock()
        mock_refresh.return_value = token_mock
        existing = MagicMock()
        mock_filter.return_value.first.return_value = existing

        serializer = UserLogoutSerializer(data={"refresh": "token"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        result = serializer.save()
        self.assertEqual(result, existing)
        token_mock.blacklist.assert_not_called()

    @patch("users.serializers.RefreshToken")
    def test_logout_serializer_raises_when_blacklist_fails(self, mock_refresh):
        token_mock = MagicMock()
        token_mock.blacklist.side_effect = Exception("fail")
        mock_refresh.return_value = token_mock

        serializer = UserLogoutSerializer(data={"refresh": "token"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(serializers.ValidationError):
            serializer.save()
