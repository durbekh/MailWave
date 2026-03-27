import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Custom exception handler for consistent API error responses."""

    # Convert Django ValidationError to DRF ValidationError
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            exc = DRFValidationError(detail=exc.message_dict)
        else:
            exc = DRFValidationError(detail=exc.messages)

    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            "error": True,
            "status_code": response.status_code,
        }

        if isinstance(response.data, dict):
            error_payload["errors"] = response.data
        elif isinstance(response.data, list):
            error_payload["errors"] = {"detail": response.data}
        else:
            error_payload["errors"] = {"detail": str(response.data)}

        # Add human-readable message
        status_messages = {
            400: "Bad request. Please check your input.",
            401: "Authentication credentials were not provided or are invalid.",
            403: "You do not have permission to perform this action.",
            404: "The requested resource was not found.",
            405: "Method not allowed.",
            429: "Too many requests. Please try again later.",
            500: "An internal server error occurred.",
        }
        error_payload["message"] = status_messages.get(
            response.status_code, "An error occurred."
        )

        response.data = error_payload
    else:
        # Unhandled exceptions
        logger.exception("Unhandled exception in API view", exc_info=exc)
        response = Response(
            {
                "error": True,
                "status_code": 500,
                "message": "An internal server error occurred.",
                "errors": {"detail": "An unexpected error occurred. Please try again later."},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


class MailWaveException(Exception):
    """Base exception for MailWave application errors."""

    def __init__(self, message="An error occurred", code=None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class EmailSendError(MailWaveException):
    """Raised when email sending fails."""
    pass


class RateLimitExceeded(MailWaveException):
    """Raised when rate limit is exceeded."""
    pass


class InvalidSegmentRule(MailWaveException):
    """Raised when a segment rule is invalid."""
    pass


class CampaignNotReady(MailWaveException):
    """Raised when campaign is not ready to send."""
    pass
