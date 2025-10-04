from django.core.exceptions import ValidationError
from django.http import Http404
from django.test import RequestFactory, TestCase
from rest_framework import status
from rest_framework.exceptions import APIException

from base.exceptions import custom_exception_handler


class CustomExceptionHandlerTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.context = {"request": self.factory.get("/")}

    def test_handles_django_validation_error(self):
        exc = ValidationError("Invalid input")
        response = custom_exception_handler(exc, self.context)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["details"], "Invalid input")
        
    def test_handles_notauthenticated_exception(self):
        exc = APIException("Not authenticated", code='not_authenticated')
        exc.status_code = status.HTTP_401_UNAUTHORIZED
        response = custom_exception_handler(exc, self.context)
        self.assertEqual(response.status_code, exc.status_code)
        self.assertEqual(response.data["details"], "Not authenticated")

    def test_handles_api_exception(self):
        exc = APIException("Forbidden")
        response = custom_exception_handler(exc, self.context)
        self.assertEqual(response.status_code, exc.status_code)
        self.assertEqual(response.data["details"], "Forbidden")

    def test_handles_http404(self):
        exc = Http404("Missing")
        response = custom_exception_handler(exc, self.context)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["details"], "Missing")

    def test_handles_unexpected_exception(self):
        exc = RuntimeError("Boom")
        response = custom_exception_handler(exc, self.context)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["details"], "An unexpected error occurred.")
