# AGENTS.md

## Commands
- **Install**: `make install` (uses uv)
- **Run tests**: `make test`
- **Single test**: `DJANGO_SETTINGS_MODULE=config.settings.test uv run python manage.py test apps.authn.tests.test_views_mobile.LoginViewTests.test_method`
- **Lint**: `make lint` / **Fix**: `make lint-fix`
- **Format**: `make format` / **Check**: `make format-check`
- **Coverage**: `make coverage`

## Code Style
- **Python 3.13**, line length 88, double quotes, 4-space indent (ruff)
- **Imports**: stdlib -> third-party (Django, DRF) -> first-party (`apps.*`, `config.*`) -> local
- **No type hints** (pyright disabled) - use docstrings instead
- **Naming**: PascalCase classes, snake_case functions/variables, UPPER_SNAKE_CASE constants

## Architecture
- **Service layer**: Business logic in `*Service` classes (e.g., `AuthService`), instantiated as singletons
- **Models**: Inherit from `apps.common.models.BaseModel` (provides `id`, `public_id`, `created_at`, `updated_at`)
- **Responses**: Use `apps.common.responses` helpers (`success_response`, `error_response`, `validation_error_response`, etc.)
- **Tests**: Use `django.test.TestCase`, `unittest.mock.patch`, `APIRequestFactory`

## Response Envelope
All APIs return: `{"message": "...", "data": {...}, "errors": null, "meta": null}`

## Workflow
- **Always run `make format`, `make lint` and `make test` after any code changes**
- **New APIs/Changes**:
    - Add detailed OpenAPI spec using `drf-spectacular` decorators (`@extend_schema`) - see below.
    - **MUST** write/update unit tests for any new API or code changes.
    - **MUST** run `make format`, `make lint` and `make test` and ensure they pass. If tests fail, adjust the code or tests until they pass.

## OpenAPI Documentation Guidelines

All new API endpoints MUST include comprehensive `@extend_schema` decorators with the following:

### Required Elements
1. **operation_id**: Unique identifier (e.g., `mobile_homeowner_jobs_update`)
2. **summary**: Short description for the endpoint
3. **description**: Detailed description including:
   - What the endpoint does
   - Who can access it (permissions)
   - Any restrictions or special behavior
   - Required verifications (e.g., "Requires phone verification")
4. **tags**: Grouping tag (e.g., `["Mobile Homeowner Jobs"]`)
5. **responses**: All possible response codes with serializers or `OpenApiTypes.OBJECT`
6. **examples**: Multiple `OpenApiExample` instances for:
   - Request examples (use `request_only=True`)
   - Success response examples (use `response_only=True`, `status_codes=["200"]`)
   - Error response examples for each error code (400, 403, 404, etc.)

### Example Template
```python
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema

@extend_schema(
    operation_id="mobile_resource_action",
    request=RequestSerializer,  # For POST/PUT/PATCH
    responses={
        200: ResponseSerializer,
        400: OpenApiTypes.OBJECT,
        403: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
    },
    parameters=[  # For query parameters
        OpenApiParameter(
            name="param_name",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Parameter description",
            required=False,
            examples=[
                OpenApiExample("Example Name", value="example_value"),
            ],
        ),
    ],
    description=(
        "Detailed description of what this endpoint does. "
        "Include permission requirements and any restrictions. "
        "Mention if phone/email verification is required."
    ),
    summary="Short action summary",
    tags=["Tag Group Name"],
    examples=[
        # Request example (for POST/PUT/PATCH)
        OpenApiExample(
            "Example Request Name",
            value={
                "field1": "value1",
                "field2": "value2",
            },
            request_only=True,
        ),
        # Success response example
        OpenApiExample(
            "Success Response",
            value={
                "message": "Action completed successfully",
                "data": {
                    "public_id": "123e4567-e89b-12d3-a456-426614174000",
                    "field1": "value1",
                    # ... full response structure
                },
                "errors": None,
                "meta": None,
            },
            response_only=True,
            status_codes=["200"],
        ),
        # Error response examples
        OpenApiExample(
            "Validation Error Response",
            value={
                "message": "Validation failed",
                "data": None,
                "errors": {
                    "field1": ["Error message for field1."],
                },
                "meta": None,
            },
            response_only=True,
            status_codes=["400"],
        ),
        OpenApiExample(
            "Not Found Response",
            value={
                "message": "Resource not found",
                "data": None,
                "errors": {"detail": "The requested resource was not found"},
                "meta": None,
            },
            response_only=True,
            status_codes=["404"],
        ),
    ],
)
def method(self, request):
    ...
```

### For List Endpoints with Pagination
Include `meta` with pagination info in success response example:
```python
"meta": {
    "pagination": {
        "page": 1,
        "page_size": 20,
        "total_pages": 3,
        "total_count": 45,
        "has_next": True,
        "has_previous": False,
    }
}
```

### Reference
See `apps/jobs/views/mobile.py` `ForYouJobListView` and `JobDetailView` for comprehensive examples.
