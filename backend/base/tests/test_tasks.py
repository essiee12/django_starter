from django.test import SimpleTestCase
from unittest.mock import patch

from base.tasks import session_cleanup


class SessionCleanupTaskTests(SimpleTestCase):
    @patch("base.tasks.management.call_command")
    def test_calls_clearsessions(self, mock_call_command):
        session_cleanup()
        mock_call_command.assert_called_once_with("clearsessions", verbosity=0)
