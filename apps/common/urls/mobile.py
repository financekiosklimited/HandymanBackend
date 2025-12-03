"""
Mobile common URL configuration.
"""

from django.urls import path

from ..views import CountryPhoneCodeListView

urlpatterns = [
    path(
        "country-codes/",
        CountryPhoneCodeListView.as_view(),
        name="mobile_country_codes_list",
    ),
]
