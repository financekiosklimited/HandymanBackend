"""
URL configuration for sb project.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import health_check

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Health check
    path("health/", health_check, name="health_check"),
    # API routes
    path("api/v1/web/", include("apps.authn.urls.web")),
    path("api/v1/web/", include("apps.profiles.urls.web")),
    path("api/v1/web/", include("apps.waitlist.urls.web")),
    path("api/v1/mobile/", include("apps.authn.urls.mobile")),
    path("api/v1/mobile/", include("apps.profiles.urls.mobile")),
    path("api/v1/mobile/", include("apps.jobs.urls.mobile")),
    path("api/v1/mobile/", include("apps.common.urls.mobile")),
    path("api/v1/mobile/", include("apps.notifications.urls.mobile")),
    # API Schema and Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
