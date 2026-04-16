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
- **Always run `make format`, `make lint`, `make test`, and `make coverage` after any code changes**
- **Coverage must always be 100% for any change. If coverage drops, add/update tests until it returns to 100%.**
- **New APIs/Changes**:
    - Add detailed OpenAPI spec using `drf-spectacular` decorators (`@extend_schema`) - see below.
    - **MUST** write/update unit tests for any new API or code changes.
    - **MUST** maintain 100% test coverage for any changes.
    - **MUST** run `make format`, `make lint`, `make test`, and `make coverage` and ensure they pass. If tests fail or coverage is below 100%, adjust the code or tests until they pass.

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

from apps.common.openapi import (
    FORBIDDEN_EXAMPLE,
    NOT_FOUND_EXAMPLE,
    UNAUTHORIZED_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
    pagination_meta_example,
)

@extend_schema(
    operation_id="mobile_resource_action",
    request=RequestSerializer,  # For POST/PUT/PATCH
    responses={
        200: ResponseSerializer,
        400: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT,
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
                },
                "errors": None,
                "meta": None,
            },
            response_only=True,
            status_codes=["200"],
        ),
        # Use reusable error examples from apps.common.openapi
        VALIDATION_ERROR_EXAMPLE,
        UNAUTHORIZED_EXAMPLE,
        FORBIDDEN_EXAMPLE,
        NOT_FOUND_EXAMPLE,
    ],
)
def method(self, request):
    ...
```

### For List Endpoints with Pagination
Use `pagination_meta_example()` helper for consistent pagination meta:
```python
from apps.common.openapi import pagination_meta_example

OpenApiExample(
    "Success Response",
    value={
        "message": "Items retrieved successfully",
        "data": [...],
        "errors": None,
        "meta": pagination_meta_example(total_count=45, total_pages=3, has_next=True),
    },
    response_only=True,
    status_codes=["200"],
)
```

### Reusable OpenAPI Constants (from `apps/common/openapi.py`)
- `VALIDATION_ERROR_EXAMPLE` - 400 validation error response
- `UNAUTHORIZED_EXAMPLE` - 401 authentication required response
- `FORBIDDEN_EXAMPLE` - 403 permission denied response
- `NOT_FOUND_EXAMPLE` - 404 resource not found response
- `SERVICE_UNAVAILABLE_EXAMPLE` - 503 service unavailable response
- `pagination_meta_example(page, page_size, total_count, total_pages, has_next, has_previous)` - Helper function for pagination meta

### Reference
See `apps/jobs/views/mobile.py` for comprehensive examples (`ForYouJobListView`, `JobDetailView`, `JobListCreateView`).

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
