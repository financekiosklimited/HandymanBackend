import os
import django
import sys
from decimal import Decimal

# Add project root to sys.path
sys.path.append('e:\\work\\solutionbank\\backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
django.setup()

from apps.accounts.models import User, UserRole
from apps.jobs.models import Job, JobApplication, JobCategory, City
from apps.jobs.views.mobile import HandymanWorkSessionStartView
from django.test import RequestFactory

def run_test():
    print("Setting up data...")
    # Setup
    email = "testhandler_standalone@example.com"
    if not User.objects.filter(email=email).exists():
        user = User.objects.create_user(email=email, password="password")
        UserRole.objects.create(user=user, role="handyman")
    else:
        user = User.objects.get(email=email)

    if not JobCategory.objects.filter(slug="cat_standalone").exists():
        category = JobCategory.objects.create(name="CatS", slug="cat_standalone")
    else:
        category = JobCategory.objects.get(slug="cat_standalone")

    if not City.objects.filter(slug="city_standalone").exists():
        city = City.objects.create(name="CityS", slug="city_standalone", province="ON", province_code="ON")
    else:
        city = City.objects.get(slug="city_standalone")

    job = Job.objects.create(
        homeowner=user, 
        title="Test Standalone",
        category=category,
        city=city,
        status="in_progress",
        estimated_budget=Decimal("100.00"),
        address="123 St",
        latitude=Decimal("45.0"),
        longitude=Decimal("-75.0")
    )
    # No assigned handyman
    job.assigned_handyman = None
    job.save()

    # Create application
    JobApplication.objects.create(job=job, handyman=user, status="approved")

    # Test View
    view = HandymanWorkSessionStartView()
    factory = RequestFactory()
    request = factory.get('/')
    request.user = user
    view.request = request

    print("Running get_job...")
    try:
        j = view.get_job(job.public_id)
        print("SUCCESS: Found job", j.public_id)
    except Exception as e:
        print("FAILURE:", e)

if __name__ == "__main__":
    run_test()
