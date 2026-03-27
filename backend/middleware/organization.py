"""
Organization-aware middleware for MailWave.
Ensures that authenticated API requests are scoped to the user's organization.
"""

import logging
import time

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class OrganizationMiddleware(MiddlewareMixin):
    """
    Middleware that validates the user has an active organization
    for API endpoints that require it.
    """

    EXEMPT_PATHS = [
        "/api/auth/register/",
        "/api/auth/login/",
        "/api/auth/refresh/",
        "/api/auth/plans/",
        "/api/analytics/t/",
        "/api/analytics/unsubscribe/",
        "/admin/",
        "/static/",
        "/media/",
    ]

    def process_request(self, request):
        # Skip non-API requests and exempt paths
        if not request.path.startswith("/api/"):
            return None

        for exempt in self.EXEMPT_PATHS:
            if request.path.startswith(exempt):
                return None

        # Skip if user is not authenticated (DRF handles auth errors)
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return None

        # Check organization
        if not request.user.organization:
            return JsonResponse(
                {
                    "error": True,
                    "status_code": 403,
                    "message": "You must belong to an organization to access this resource.",
                },
                status=403,
            )

        if not request.user.organization.is_active:
            return JsonResponse(
                {
                    "error": True,
                    "status_code": 403,
                    "message": "Your organization has been deactivated.",
                },
                status=403,
            )

        return None


class RequestTimingMiddleware(MiddlewareMixin):
    """
    Middleware that adds X-Request-Duration header to all responses
    for performance monitoring.
    """

    def process_request(self, request):
        request._start_time = time.monotonic()

    def process_response(self, request, response):
        if hasattr(request, "_start_time"):
            duration_ms = (time.monotonic() - request._start_time) * 1000
            response["X-Request-Duration"] = f"{duration_ms:.2f}ms"

            # Log slow requests
            if duration_ms > 1000:
                logger.warning(
                    "Slow request: %s %s took %.2fms",
                    request.method, request.path, duration_ms,
                )

        return response


class APIVersionMiddleware(MiddlewareMixin):
    """
    Middleware to handle API versioning via headers.
    Adds the current API version to the response.
    """

    CURRENT_VERSION = "1.0"

    def process_response(self, request, response):
        if request.path.startswith("/api/"):
            response["X-API-Version"] = self.CURRENT_VERSION
        return response
