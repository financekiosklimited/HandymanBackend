"""
Custom exception handler for consistent JSON responses.
"""

from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Custom exception handler that wraps responses in consistent JSON envelope.
    Only applies to endpoints that return a body (not 202/204).
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Check if this is a no-body response endpoint
        if response.status_code in [202, 204]:
            return response

        # Create custom response data with envelope format
        custom_response_data = {
            "message": get_error_message(exc, response),
            "data": None,
            "errors": get_error_details(exc, response),
            "meta": None,
        }

        response.data = custom_response_data

    return response


def get_error_message(exc, response):
    """
    Get appropriate error message based on exception type.
    """
    status_code = response.status_code

    # Map status codes to default messages
    status_messages = {
        400: "Bad request",
        401: "Authentication required",
        403: "Permission denied",
        404: "Not found",
        405: "Method not allowed",
        409: "Conflict",
        422: "Unprocessable entity",
        429: "Rate limit exceeded",
        500: "Internal server error",
    }

    # Check if response data has a custom message
    if hasattr(response, "data") and isinstance(response.data, dict):
        if "message" in response.data:
            return response.data["message"]

        # Check for detail field
        if "detail" in response.data:
            return str(response.data["detail"])

    # Use status code default or exception string
    return status_messages.get(status_code, str(exc))


def get_error_details(exc, response):
    """
    Get error details from exception and response.
    """
    if hasattr(response, "data") and response.data:
        data = response.data

        # If data already has errors field, use it
        if isinstance(data, dict) and "errors" in data:
            return data["errors"]

        # If data is already in envelope format, extract errors
        if isinstance(data, dict) and all(
            key in data for key in ["message", "data", "errors", "meta"]
        ):
            return data.get("errors")

        # For validation errors, return the data as errors
        if isinstance(data, dict) and response.status_code == 400:
            # Remove message/detail fields from errors
            errors = {k: v for k, v in data.items() if k not in ["message", "detail"]}
            if errors:
                return errors

        # For single detail messages
        if isinstance(data, dict) and "detail" in data:
            return {"detail": str(data["detail"])}

        # Return the data as-is if it's a dict
        if isinstance(data, dict):
            return data

    # Default error details
    return {"detail": str(exc)}
