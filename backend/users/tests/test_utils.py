from django.test import SimpleTestCase

from users.utils import generate_otp


class GenerateOtpTests(SimpleTestCase):
    def test_returns_six_digit_numeric_string(self):
        otp = generate_otp()
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())
        self.assertNotEqual(otp[0], "0")

    def test_can_generate_multiple_unique_codes(self):
        otps = {generate_otp() for _ in range(10)}
        self.assertGreater(len(otps), 1)
