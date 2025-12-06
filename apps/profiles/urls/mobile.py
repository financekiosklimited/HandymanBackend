"""
Mobile profile URL configuration.
"""

from django.urls import path

from ..views import mobile as mobile_views

urlpatterns = [
    # Role-specific profile endpoints
    path(
        "homeowner/profile",
        mobile_views.HomeownerProfileView.as_view(),
        name="mobile_homeowner_profile",
    ),
    path(
        "handyman/profile",
        mobile_views.HandymanProfileView.as_view(),
        name="mobile_handyman_profile",
    ),
]
