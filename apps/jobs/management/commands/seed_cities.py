from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.jobs.models import City


class Command(BaseCommand):
    help = "Seed major Canadian cities"

    def handle(self, *args, **options):
        cities_data = [
            # Ontario
            {
                "name": "Toronto",
                "province": "Ontario",
                "province_code": "ON",
                "slug": "toronto-on",
                "latitude": Decimal("43.651070"),
                "longitude": Decimal("-79.347015"),
            },
            {
                "name": "Ottawa",
                "province": "Ontario",
                "province_code": "ON",
                "slug": "ottawa-on",
                "latitude": Decimal("45.421530"),
                "longitude": Decimal("-75.697193"),
            },
            {
                "name": "Mississauga",
                "province": "Ontario",
                "province_code": "ON",
                "slug": "mississauga-on",
                "latitude": Decimal("43.589045"),
                "longitude": Decimal("-79.644120"),
            },
            {
                "name": "Hamilton",
                "province": "Ontario",
                "province_code": "ON",
                "slug": "hamilton-on",
                "latitude": Decimal("43.255203"),
                "longitude": Decimal("-79.843826"),
            },
            # British Columbia
            {
                "name": "Vancouver",
                "province": "British Columbia",
                "province_code": "BC",
                "slug": "vancouver-bc",
                "latitude": Decimal("49.282729"),
                "longitude": Decimal("-123.120738"),
            },
            {
                "name": "Surrey",
                "province": "British Columbia",
                "province_code": "BC",
                "slug": "surrey-bc",
                "latitude": Decimal("49.105800"),
                "longitude": Decimal("-122.825095"),
            },
            # Alberta
            {
                "name": "Calgary",
                "province": "Alberta",
                "province_code": "AB",
                "slug": "calgary-ab",
                "latitude": Decimal("51.044733"),
                "longitude": Decimal("-114.071883"),
            },
            {
                "name": "Edmonton",
                "province": "Alberta",
                "province_code": "AB",
                "slug": "edmonton-ab",
                "latitude": Decimal("53.544389"),
                "longitude": Decimal("-113.490927"),
            },
            # Quebec
            {
                "name": "Montreal",
                "province": "Quebec",
                "province_code": "QC",
                "slug": "montreal-qc",
                "latitude": Decimal("45.501689"),
                "longitude": Decimal("-73.567256"),
            },
            {
                "name": "Quebec City",
                "province": "Quebec",
                "province_code": "QC",
                "slug": "quebec-city-qc",
                "latitude": Decimal("46.813878"),
                "longitude": Decimal("-71.207981"),
            },
            # Manitoba
            {
                "name": "Winnipeg",
                "province": "Manitoba",
                "province_code": "MB",
                "slug": "winnipeg-mb",
                "latitude": Decimal("49.895136"),
                "longitude": Decimal("-97.138374"),
            },
            # Nova Scotia
            {
                "name": "Halifax",
                "province": "Nova Scotia",
                "province_code": "NS",
                "slug": "halifax-ns",
                "latitude": Decimal("44.648618"),
                "longitude": Decimal("-63.585948"),
            },
        ]

        created_count = 0
        updated_count = 0

        for city_data in cities_data:
            city, created = City.objects.update_or_create(
                name=city_data["name"],
                province=city_data["province"],
                defaults={
                    "province_code": city_data["province_code"],
                    "slug": city_data["slug"],
                    "latitude": city_data["latitude"],
                    "longitude": city_data["longitude"],
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded cities: {created_count} created, {updated_count} updated"
            )
        )
