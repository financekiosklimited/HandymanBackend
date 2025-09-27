"""
Common response utilities for consistent JSON envelope format.
"""

from rest_framework import status
from rest_framework.response import Response


def success_response(
    data=None, message="Success", meta=None, status_code=status.HTTP_200_OK
):
    """
    Create a successful response with consistent envelope format.

    Args:
        data: Response data
        message: Success message
        meta: Additional metadata
        status_code: HTTP status code

    Returns:
        Response: DRF Response object
    """
    return Response(
        {"message": message, "data": data, "errors": None, "meta": meta},
        status=status_code,
    )


def error_response(
    errors=None,
    message="Error",
    data=None,
    meta=None,
    status_code=status.HTTP_400_BAD_REQUEST,
):
    """
    Create an error response with consistent envelope format.

    Args:
        errors: Error details
        message: Error message
        data: Response data (usually None for errors)
        meta: Additional metadata
        status_code: HTTP status code

    Returns:
        Response: DRF Response object
    """
    return Response(
        {"message": message, "data": data, "errors": errors, "meta": meta},
        status=status_code,
    )


def created_response(data=None, message="Created", meta=None):
    """
    Create a 201 Created response.
    """
    return success_response(data, message, meta, status.HTTP_201_CREATED)


def accepted_response(message="Accepted"):
    """
    Create a 202 Accepted response with no body.
    """
    return Response(status=status.HTTP_202_ACCEPTED)


def no_content_response():
    """
    Create a 204 No Content response.
    """
    return Response(status=status.HTTP_204_NO_CONTENT)


def validation_error_response(errors, message="Validation failed"):
    """
    Create a 400 Bad Request response for validation errors.
    """
    return error_response(errors, message, status_code=status.HTTP_400_BAD_REQUEST)


def unauthorized_response(message="Authentication required"):
    """
    Create a 401 Unauthorized response.
    """
    return error_response(
        errors={"auth": "Authentication credentials were not provided"},
        message=message,
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


def forbidden_response(errors=None, message="Permission denied"):
    """
    Create a 403 Forbidden response.
    """
    return error_response(errors, message, status_code=status.HTTP_403_FORBIDDEN)


def not_found_response(message="Not found"):
    """
    Create a 404 Not Found response.
    """
    return error_response(
        errors={"detail": "The requested resource was not found"},
        message=message,
        status_code=status.HTTP_404_NOT_FOUND,
    )


def conflict_response(errors=None, message="Conflict"):
    """
    Create a 409 Conflict response.
    """
    return error_response(errors, message, status_code=status.HTTP_409_CONFLICT)


def throttled_response(message="Rate limit exceeded"):
    """
    Create a 429 Too Many Requests response.
    """
    return error_response(
        errors={"throttle": "Request was throttled"},
        message=message,
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    )
