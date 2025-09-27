"""
Web profile URL configuration.
"""

from django.urls import path
from ..views import web as web_views

urlpatterns = [
    # Role-specific profile endpoints
    path(
        "customer/profile",
        web_views.CustomerProfileView.as_view(),
        name="web_customer_profile",
    ),
    path(
        "handyman/profile",
        web_views.HandymanProfileView.as_view(),
        name="web_handyman_profile",
    ),
]
