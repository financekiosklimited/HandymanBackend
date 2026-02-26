"""
URL patterns for Discounts app.
"""

from django.urls import include, path

app_name = "discounts"

urlpatterns = [
    # Mobile API endpoints
    path("mobile/", include("apps.discounts.urls.mobile", namespace="mobile")),
]
