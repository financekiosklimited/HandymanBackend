"""
Mobile profile URL configuration.
"""

from django.urls import path

from ..views import mobile as mobile_views

urlpatterns = [
    # Handyman Categories (public, no auth required)
    path(
        "handyman-categories/",
        mobile_views.HandymanCategoryListView.as_view(),
        name="mobile_handyman_categories",
    ),
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
    path(
        "homeowner/handymen/<uuid:public_id>/reviews/",
        mobile_views.HomeownerHandymanReviewListView.as_view(),
        name="mobile_homeowner_handyman_reviews",
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
    path(
        "guest/handymen/<uuid:public_id>/reviews/",
        mobile_views.GuestHandymanReviewListView.as_view(),
        name="mobile_guest_handyman_reviews",
    ),
]
