"""
Mobile URL patterns for Discounts app.
"""

from django.urls import path

from ..views.mobile import (
    DiscountDetailView,
    DiscountListView,
    DiscountValidateView,
)

app_name = "discounts_mobile"

urlpatterns = [
    path("", DiscountListView.as_view(), name="discount-list"),
    path("validate/", DiscountValidateView.as_view(), name="discount-validate"),
    path("<str:code>/", DiscountDetailView.as_view(), name="discount-detail"),
]
