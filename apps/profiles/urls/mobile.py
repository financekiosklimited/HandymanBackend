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
    # Homeowner handyman browsing
    path(
        "homeowner/handymen/nearby/",
        mobile_views.HomeownerNearbyHandymanListView.as_view(),
        name="mobile_homeowner_handymen_nearby",
    ),
    path(
        "homeowner/handymen/<uuid:public_id>/",
        mobile_views.HomeownerHandymanDetailView.as_view(),
        name="mobile_homeowner_handyman_detail",
    ),
    # Guest handyman endpoints (no authentication required)
    path(
        "guest/handymen/",
        mobile_views.GuestHandymanListView.as_view(),
        name="mobile_guest_handymen",
    ),
    path(
        "guest/handymen/<uuid:public_id>/",
        mobile_views.GuestHandymanDetailView.as_view(),
        name="mobile_guest_handyman_detail",
    ),
]
