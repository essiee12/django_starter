from unittest.mock import patch

from django.test import TestCase

from users.models import UserOtp
from users.tasks import delete_user_otp, send_otp_to_user_mail
from users.tests.factories import UserFactory, UserOtpFactory


class SendOtpTaskTests(TestCase):
    @patch("users.tasks.delete_user_otp.apply_async")
    @patch("users.tasks.send_mail")
    @patch("users.tasks.render_to_string", return_value="otp")
    def test_send_otp_creates_or_updates_record_and_dispatches_email(
        self, mock_render, mock_send_mail, mock_apply_async
    ):
        user = UserFactory.create()

        send_otp_to_user_mail(user.email)

        otp_record = UserOtp.objects.get(email=user.email)
        self.assertEqual(len(str(otp_record.otp)), 6)

        mock_render.assert_called_once()
        mock_send_mail.assert_called_once()
        mock_apply_async.assert_called_once()

    @patch("users.tasks.delete_user_otp.apply_async")
    @patch("users.tasks.send_mail")
    @patch("users.tasks.render_to_string")
    def test_send_otp_noops_when_user_missing(
        self, mock_render, mock_send_mail, mock_apply_async
    ):
        send_otp_to_user_mail("missing@example.com")

        self.assertFalse(UserOtp.objects.filter(email="missing@example.com").exists())
        mock_render.assert_not_called()
        mock_send_mail.assert_not_called()
        mock_apply_async.assert_not_called()


class DeleteOtpTaskTests(TestCase):
    def test_delete_user_otp_removes_record(self):
        otp = UserOtpFactory.create(email="otp@example.com")
        delete_user_otp(otp.email)
        self.assertFalse(UserOtp.objects.filter(email="otp@example.com").exists())

    def test_delete_user_otp_is_safe_when_missing(self):
        # Should not raise
        delete_user_otp("missing@example.com")
        self.assertFalse(UserOtp.objects.filter(email="missing@example.com").exists())
