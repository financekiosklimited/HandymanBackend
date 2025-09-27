"""
Mobile profile URL configuration.
"""

from django.urls import path
from ..views import mobile as mobile_views

urlpatterns = [
    # Role-specific profile endpoints
    path(
        "customer/profile",
        mobile_views.CustomerProfileView.as_view(),
        name="mobile_customer_profile",
    ),
    path(
        "handyman/profile",
        mobile_views.HandymanProfileView.as_view(),
        name="mobile_handyman_profile",
    ),
]
