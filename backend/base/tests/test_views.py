from django.contrib.auth import get_user_model
from django.test import TestCase


class BaseViewsTests(TestCase):
    def test_ping_view_returns_pong(self):
        response = self.client.get("/ping")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "pong")

    def test_settings_view_requires_superuser(self):
        user = get_user_model().objects.create_user(
            email="user@example.com", password="password123"
        )
        self.client.force_login(user)

        response = self.client.get("/iconfig")
        self.assertEqual(response.status_code, 302)

    def test_settings_view_returns_sanitized_settings_for_superuser(self):
        User = get_user_model()
        superuser = User.objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        self.client.force_login(superuser)

        response = self.client.get("/iconfig")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("SECRET", content)
        self.assertIn("DJANGO", content)
