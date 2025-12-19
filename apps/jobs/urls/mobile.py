from django.urls import path

from ..views import mobile as mobile_views

urlpatterns = [
    # Supporting endpoints (no role required)
    path(
        "job-categories/",
        mobile_views.JobCategoryListView.as_view(),
        name="mobile_job_categories",
    ),
    path(
        "cities/",
        mobile_views.CityListView.as_view(),
        name="mobile_cities",
    ),
    # Homeowner job endpoints
    path(
        "homeowner/jobs/",
        mobile_views.JobListCreateView.as_view(),
        name="mobile_homeowner_jobs",
    ),
    path(
        "homeowner/jobs/for-you/",
        mobile_views.ForYouJobListView.as_view(),
        name="mobile_homeowner_jobs_for_you",
    ),
    path(
        "homeowner/jobs/<uuid:public_id>/",
        mobile_views.JobDetailView.as_view(),
        name="mobile_homeowner_job_detail",
    ),
    # Guest job endpoints (no authentication required)
    path(
        "guest/jobs/",
        mobile_views.GuestJobListView.as_view(),
        name="mobile_guest_jobs",
    ),
    path(
        "guest/jobs/<uuid:public_id>/",
        mobile_views.GuestJobDetailView.as_view(),
        name="mobile_guest_job_detail",
    ),
    # Handyman job browsing endpoints
    path(
        "handyman/jobs/for-you/",
        mobile_views.HandymanForYouJobListView.as_view(),
        name="mobile_handyman_jobs_for_you",
    ),
    path(
        "handyman/jobs/<uuid:public_id>/",
        mobile_views.HandymanJobDetailView.as_view(),
        name="mobile_handyman_job_detail",
    ),
    # Handyman application endpoints
    path(
        "handyman/applications/",
        mobile_views.HandymanJobApplicationListCreateView.as_view(),
        name="mobile_handyman_applications",
    ),
    path(
        "handyman/applications/<uuid:public_id>/",
        mobile_views.HandymanJobApplicationDetailView.as_view(),
        name="mobile_handyman_application_detail",
    ),
    path(
        "handyman/applications/<uuid:public_id>/withdraw/",
        mobile_views.HandymanJobApplicationWithdrawView.as_view(),
        name="mobile_handyman_application_withdraw",
    ),
    # Homeowner application management endpoints (global)
    path(
        "homeowner/applications/",
        mobile_views.HomeownerApplicationListView.as_view(),
        name="mobile_homeowner_applications",
    ),
    path(
        "homeowner/applications/<uuid:public_id>/",
        mobile_views.HomeownerApplicationDetailView.as_view(),
        name="mobile_homeowner_application_detail",
    ),
    path(
        "homeowner/applications/<uuid:public_id>/approve/",
        mobile_views.HomeownerApplicationApproveView.as_view(),
        name="mobile_homeowner_application_approve",
    ),
    path(
        "homeowner/applications/<uuid:public_id>/reject/",
        mobile_views.HomeownerApplicationRejectView.as_view(),
        name="mobile_homeowner_application_reject",
    ),
]
