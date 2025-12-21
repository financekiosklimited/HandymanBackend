from django.core.management.base import BaseCommand

from apps.jobs.models import JobCategory


class Command(BaseCommand):
    help = "Seed job categories"

    def handle(self, *args, **options):
        categories_data = [
            {
                "name": "Plumbing",
                "slug": "plumbing",
                "description": "Plumbing services including repairs, installations, and maintenance",
                "icon": "plumbing",
            },
            {
                "name": "Electrical",
                "slug": "electrical",
                "description": "Electrical work including wiring, repairs, and installations",
                "icon": "electrical_services",
            },
            {
                "name": "Carpentry",
                "slug": "carpentry",
                "description": "Carpentry and woodworking services",
                "icon": "carpenter",
            },
            {
                "name": "Cleaning",
                "slug": "cleaning",
                "description": "Home and office cleaning services",
                "icon": "cleaning_services",
            },
            {
                "name": "Painting",
                "slug": "painting",
                "description": "Interior and exterior painting services",
                "icon": "format_paint",
            },
            {
                "name": "Landscaping",
                "slug": "landscaping",
                "description": "Lawn care, gardening, and outdoor maintenance",
                "icon": "yard",
            },
            {
                "name": "HVAC",
                "slug": "hvac",
                "description": "Heating, ventilation, and air conditioning services",
                "icon": "ac_unit",
            },
            {
                "name": "Roofing",
                "slug": "roofing",
                "description": "Roof repair, installation, and maintenance",
                "icon": "roofing",
            },
            {
                "name": "Flooring",
                "slug": "flooring",
                "description": "Floor installation, repair, and refinishing",
                "icon": "layers",
            },
            {
                "name": "Appliance Repair",
                "slug": "appliance-repair",
                "description": "Repair and maintenance of home appliances",
                "icon": "home_repair_service",
            },
        ]

        created_count = 0
        updated_count = 0

        for cat_data in categories_data:
            category, created = JobCategory.objects.update_or_create(
                slug=cat_data["slug"],
                defaults={
                    "name": cat_data["name"],
                    "description": cat_data["description"],
                    "icon": cat_data["icon"],
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        if options["verbosity"] > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully seeded categories: {created_count} created, {updated_count} updated"
                )
            )
