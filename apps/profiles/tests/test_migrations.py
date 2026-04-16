"""Migration tests for profiles app."""

from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class HandymanCurrentCityBackfillMigrationTests(TransactionTestCase):
    """Test handyman current-city backfill migration."""

    migrate_from = ("profiles", "0010_homeowner_profile_location_fields")
    migrate_to = ("profiles", "0011_backfill_handyman_current_city")

    def setUp(self):
        """Migrate to the old state, seed rows, then migrate forward."""
        self.executor = MigrationExecutor(connection)
        self.leaf_targets = self.executor.loader.graph.leaf_nodes()
        self.migrate_from_targets = [
            target for target in self.leaf_targets if target[0] != "profiles"
        ] + [self.migrate_from]
        self.migrate_to_targets = [
            target for target in self.leaf_targets if target[0] != "profiles"
        ] + [self.migrate_to]

        self.executor.migrate(self.migrate_from_targets)
        old_apps = self.executor.loader.project_state(self.migrate_from_targets).apps
        self.set_up_before_migration(old_apps)

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to_targets)
        self.apps = self.executor.loader.project_state(self.migrate_to_targets).apps

    def set_up_before_migration(self, old_apps):
        """Seed handymen and cities before applying the backfill migration."""
        City = old_apps.get_model("jobs", "City")
        User = old_apps.get_model("accounts", "User")
        HandymanProfile = old_apps.get_model("profiles", "HandymanProfile")

        self.toronto = City.objects.create(
            name="Toronto",
            province="Ontario",
            province_code="ON",
            slug="toronto-on",
            latitude=Decimal("43.653226"),
            longitude=Decimal("-79.383184"),
            is_active=True,
        )
        self.ottawa = City.objects.create(
            name="Ottawa",
            province="Ontario",
            province_code="ON",
            slug="ottawa-on",
            latitude=Decimal("45.421530"),
            longitude=Decimal("-75.697193"),
            is_active=True,
        )

        nearby_user = User.objects.create(
            email="backfill-nearby@example.com",
            password="testpass123",
        )
        self.nearby_profile_id = HandymanProfile.objects.create(
            user=nearby_user,
            display_name="Nearby Handyman",
            latitude=Decimal("43.650000"),
            longitude=Decimal("-79.360000"),
        ).id

        missing_coords_user = User.objects.create(
            email="backfill-missing@example.com",
            password="testpass123",
        )
        self.missing_coords_profile_id = HandymanProfile.objects.create(
            user=missing_coords_user,
            display_name="Missing Coordinates",
        ).id

        existing_city_user = User.objects.create(
            email="backfill-existing@example.com",
            password="testpass123",
        )
        self.existing_city_profile_id = HandymanProfile.objects.create(
            user=existing_city_user,
            display_name="Existing City",
            latitude=Decimal("43.650000"),
            longitude=Decimal("-79.360000"),
            current_city=self.ottawa,
        ).id

    def test_migration_backfills_current_city_for_geocoded_handymen(self):
        """Migration fills current_city only for geocoded handymen missing it."""
        HandymanProfile = self.apps.get_model("profiles", "HandymanProfile")

        nearby_profile = HandymanProfile.objects.get(id=self.nearby_profile_id)
        self.assertIsNotNone(nearby_profile.current_city)
        self.assertEqual(nearby_profile.current_city.slug, "toronto-on")

        missing_coords_profile = HandymanProfile.objects.get(
            id=self.missing_coords_profile_id
        )
        self.assertIsNone(missing_coords_profile.current_city)

        existing_city_profile = HandymanProfile.objects.get(
            id=self.existing_city_profile_id
        )
        self.assertEqual(existing_city_profile.current_city.slug, "ottawa-on")
