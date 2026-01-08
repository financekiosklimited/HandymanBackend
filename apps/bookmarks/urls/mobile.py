"""
Mobile URL configuration for bookmarks.
"""

from django.urls import path

from ..views import mobile as mobile_views

urlpatterns = [
    # Handyman job bookmarks
    path(
        "handyman/bookmarks/jobs/",
        mobile_views.HandymanJobBookmarkListCreateView.as_view(),
        name="mobile_handyman_bookmarks_jobs",
    ),
    path(
        "handyman/bookmarks/jobs/<uuid:job_id>/",
        mobile_views.HandymanJobBookmarkDeleteView.as_view(),
        name="mobile_handyman_bookmarks_jobs_delete",
    ),
    # Homeowner handyman bookmarks
    path(
        "homeowner/bookmarks/handymen/",
        mobile_views.HomeownerHandymanBookmarkListCreateView.as_view(),
        name="mobile_homeowner_bookmarks_handymen",
    ),
    path(
        "homeowner/bookmarks/handymen/<uuid:handyman_id>/",
        mobile_views.HomeownerHandymanBookmarkDeleteView.as_view(),
        name="mobile_homeowner_bookmarks_handymen_delete",
    ),
]
