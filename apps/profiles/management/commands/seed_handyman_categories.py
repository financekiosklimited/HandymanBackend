from django.core.management.base import BaseCommand

from apps.profiles.models import HandymanCategory


class Command(BaseCommand):
    help = "Seed initial handyman categories"

    def handle(self, *args, **options):
        categories = [
            {
                "name": "Plumbing",
                "description": "Pipe repairs, installations, and maintenance",
            },
            {
                "name": "Electrical",
                "description": "Wiring, lighting, and electrical repairs",
            },
            {
                "name": "Carpentry",
                "description": "Woodwork, furniture repair, and installation",
            },
            {
                "name": "Painting",
                "description": "Interior and exterior painting services",
            },
            {"name": "Cleaning", "description": "House and office cleaning services"},
            {"name": "Gardening", "description": "Lawn care and landscaping services"},
            {
                "name": "Masonry",
                "description": "Brickwork, tiling, and concrete services",
            },
            {
                "name": "General Repairs",
                "description": "Misc home maintenance and minor fixes",
            },
        ]

        for cat_data in categories:
            category, created = HandymanCategory.objects.get_or_create(
                name=cat_data["name"], defaults={"description": cat_data["description"]}
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created category: {category.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Category already exists: {category.name}")
                )
