import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.db import IntegrityError

from users.models import UserOtp
from users.tests.factories import UserFactory


class UserModelTests(TestCase):
    def test_factory_sets_password_hash(self):
        raw_password = "testpass123"
        user = UserFactory.create(password=raw_password)
        self.assertTrue(user.check_password(raw_password))

    def test_str_returns_full_name_or_email(self):
        user_with_name = UserFactory.create(full_name="Jane Doe")
        self.assertEqual(str(user_with_name), "Jane Doe")

        user_without_name = UserFactory.create(full_name="")
        self.assertEqual(str(user_without_name), user_without_name.email)

    def test_create_superuser(self):
        admin = UserFactory.create_superuser()
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    @patch("users.models.requests.get")
    def test_set_photo_from_url_saves_image(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"fake-bytes"

        user = UserFactory.create()

        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(MEDIA_ROOT=tmpdir):
                get_user_model().set_photo_from_url(
                    user, "http://example.com/avatar.jpg"
                )

        user.refresh_from_db()
        self.assertTrue(user.profile_picture.name.endswith(".jpg"))


class UserOtpModelTests(TestCase):
    def test_str_returns_correct_representation(self):
        otp = UserOtp.objects.create(email="test@example.com", otp="123456")
        self.assertEqual(str(otp), f"OTP for {otp.email}")

    def test_email_uniqueness(self):
        UserOtp.objects.create(email="unique@example.com", otp="654321")
        with self.assertRaises(IntegrityError):
            UserOtp.objects.create(email="unique@example.com", otp="000000")

    def test_otp_creation_stores_correct_data(self):
        otp = UserOtp.objects.create(email="verify@example.com", otp="789012")
        self.assertEqual(otp.email, "verify@example.com")
        self.assertEqual(otp.otp, "789012")
        self.assertIsNotNone(otp.created_at)
