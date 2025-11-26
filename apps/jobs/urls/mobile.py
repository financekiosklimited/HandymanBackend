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
    # Customer job endpoints
    path(
        "customer/jobs/",
        mobile_views.JobListCreateView.as_view(),
        name="mobile_customer_jobs",
    ),
    path(
        "customer/jobs/<uuid:public_id>/",
        mobile_views.JobDetailView.as_view(),
        name="mobile_customer_job_detail",
    ),
]
