from rest_framework.exceptions import APIException, NotAuthenticated
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.http import Http404
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom Exception Handler method. This will
    """
    response = exception_handler(exc, context)
    error_data = {}
    if isinstance(exc, ValidationError):
        error_data["details"] = exc.message
        response = Response(error_data, status=status.HTTP_400_BAD_REQUEST)

    elif isinstance(exc, NotAuthenticated):
        error_data["detail"] = str(exc.detail)
        return Response(error_data, status=status.HTTP_401_UNAUTHORIZED)

    elif isinstance(exc, APIException):
        error_data["details"] = exc.detail
        response = Response(error_data, status=exc.status_code)

    elif isinstance(exc, Http404):
        error_data["details"] = str(exc)
        response = Response(error_data, status=status.HTTP_404_NOT_FOUND)

    else:
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        error_data["details"] = _("An unexpected error occurred.")
        response = Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
