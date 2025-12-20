from drf_spectacular.utils import OpenApiExample


def pagination_meta_example(
    page=1,
    page_size=20,
    total_count=1,
    total_pages=1,
    has_next=False,
    has_previous=False,
):
    """
    Helper function to generate consistent pagination meta examples.
    """
    return {
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_count": total_count,
            "has_next": has_next,
            "has_previous": has_previous,
        }
    }


# Common Error Response Examples
VALIDATION_ERROR_EXAMPLE = OpenApiExample(
    "Validation Error Response",
    value={
        "message": "Validation failed",
        "data": None,
        "errors": {
            "field_name": ["This field is required."],
            "another_field": ["Enter a valid email address."],
        },
        "meta": None,
    },
    response_only=True,
    status_codes=["400"],
)

UNAUTHORIZED_EXAMPLE = OpenApiExample(
    "Unauthorized Response",
    value={
        "message": "Authentication credentials were not provided",
        "data": None,
        "errors": {"detail": "Authentication credentials were not provided."},
        "meta": None,
    },
    response_only=True,
    status_codes=["401"],
)

FORBIDDEN_EXAMPLE = OpenApiExample(
    "Forbidden Response",
    value={
        "message": "You do not have permission to perform this action",
        "data": None,
        "errors": {"detail": "You do not have permission to perform this action."},
        "meta": None,
    },
    response_only=True,
    status_codes=["403"],
)

NOT_FOUND_EXAMPLE = OpenApiExample(
    "Not Found Response",
    value={
        "message": "Resource not found",
        "data": None,
        "errors": {"detail": "The requested resource was not found"},
        "meta": None,
    },
    response_only=True,
    status_codes=["404"],
)

SERVICE_UNAVAILABLE_EXAMPLE = OpenApiExample(
    "Service Unavailable Response",
    value={
        "message": "Service temporarily unavailable",
        "data": None,
        "errors": {
            "detail": "Failed to connect to external service. Please try again later."
        },
        "meta": None,
    },
    response_only=True,
    status_codes=["503"],
)
