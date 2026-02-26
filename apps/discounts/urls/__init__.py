"""
URL patterns for Discounts app.
"""

from django.urls import include, path

app_name = "discounts"

urlpatterns = [
    # Mobile API endpoints
    path("discounts/", include("apps.discounts.urls.mobile", namespace="mobile")),
]
