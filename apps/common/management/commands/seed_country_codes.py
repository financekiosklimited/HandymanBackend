"""
Management command to seed country phone codes.
"""

from django.core.management.base import BaseCommand

from apps.common.models import CountryPhoneCode


class Command(BaseCommand):
    help = "Seed country phone codes for phone verification"

    # Country codes data: Indonesia, Canada, and Arab countries
    COUNTRY_CODES = [
        # Priority countries
        {
            "country_code": "ID",
            "country_name": "Indonesia",
            "dial_code": "+62",
            "flag_emoji": "",
            "display_order": 1,
        },
        {
            "country_code": "CA",
            "country_name": "Canada",
            "dial_code": "+1",
            "flag_emoji": "",
            "display_order": 2,
        },
        # Arab countries
        {
            "country_code": "AE",
            "country_name": "United Arab Emirates",
            "dial_code": "+971",
            "flag_emoji": "",
            "display_order": 3,
        },
        {
            "country_code": "SA",
            "country_name": "Saudi Arabia",
            "dial_code": "+966",
            "flag_emoji": "",
            "display_order": 4,
        },
        {
            "country_code": "QA",
            "country_name": "Qatar",
            "dial_code": "+974",
            "flag_emoji": "",
            "display_order": 5,
        },
        {
            "country_code": "KW",
            "country_name": "Kuwait",
            "dial_code": "+965",
            "flag_emoji": "",
            "display_order": 6,
        },
        {
            "country_code": "BH",
            "country_name": "Bahrain",
            "dial_code": "+973",
            "flag_emoji": "",
            "display_order": 7,
        },
        {
            "country_code": "OM",
            "country_name": "Oman",
            "dial_code": "+968",
            "flag_emoji": "",
            "display_order": 8,
        },
        {
            "country_code": "JO",
            "country_name": "Jordan",
            "dial_code": "+962",
            "flag_emoji": "",
            "display_order": 9,
        },
        {
            "country_code": "EG",
            "country_name": "Egypt",
            "dial_code": "+20",
            "flag_emoji": "",
            "display_order": 10,
        },
        {
            "country_code": "LB",
            "country_name": "Lebanon",
            "dial_code": "+961",
            "flag_emoji": "",
            "display_order": 11,
        },
        {
            "country_code": "IQ",
            "country_name": "Iraq",
            "dial_code": "+964",
            "flag_emoji": "",
            "display_order": 12,
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force update existing country codes",
        )

    def handle(self, *args, **options):
        force = options["force"]
        created_count = 0
        updated_count = 0

        for country_data in self.COUNTRY_CODES:
            country_code = country_data["country_code"]

            if force:
                # Update or create
                obj, created = CountryPhoneCode.objects.update_or_create(
                    country_code=country_code,
                    defaults={
                        "country_name": country_data["country_name"],
                        "dial_code": country_data["dial_code"],
                        "flag_emoji": country_data["flag_emoji"],
                        "display_order": country_data["display_order"],
                        "is_active": True,
                    },
                )
                if created:
                    created_count += 1
                    self.stdout.write(f"  Created: {country_data['country_name']}")
                else:
                    updated_count += 1
                    self.stdout.write(f"  Updated: {country_data['country_name']}")
            else:
                # Only create if not exists
                obj, created = CountryPhoneCode.objects.get_or_create(
                    country_code=country_code,
                    defaults={
                        "country_name": country_data["country_name"],
                        "dial_code": country_data["dial_code"],
                        "flag_emoji": country_data["flag_emoji"],
                        "display_order": country_data["display_order"],
                        "is_active": True,
                    },
                )
                if created:
                    created_count += 1
                    self.stdout.write(f"  Created: {country_data['country_name']}")
                else:
                    self.stdout.write(
                        f"  Skipped (exists): {country_data['country_name']}"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeding complete! Created: {created_count}, Updated: {updated_count}"
            )
        )
