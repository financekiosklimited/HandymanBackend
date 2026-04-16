import math

from django.db import migrations


def calculate_distance_km(latitude, longitude, city_latitude, city_longitude):
    """Calculate the Haversine distance between two coordinate pairs."""
    earth_radius_km = 6371

    latitude_radians = math.radians(float(latitude))
    longitude_radians = math.radians(float(longitude))
    city_latitude_radians = math.radians(float(city_latitude))
    city_longitude_radians = math.radians(float(city_longitude))

    delta_latitude = city_latitude_radians - latitude_radians
    delta_longitude = city_longitude_radians - longitude_radians

    haversine = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude_radians)
        * math.cos(city_latitude_radians)
        * math.sin(delta_longitude / 2) ** 2
    )
    arc = 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))

    return earth_radius_km * arc


def backfill_handyman_current_city(apps, schema_editor):
    """Populate current_city for existing geocoded handymen missing it."""
    City = apps.get_model("jobs", "City")
    HandymanProfile = apps.get_model("profiles", "HandymanProfile")

    cities = list(
        City.objects.filter(
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )
    )

    if not cities:
        return

    for profile in HandymanProfile.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        current_city__isnull=True,
    ).iterator():
        nearest_city = None
        nearest_distance = None

        for city in cities:
            distance = calculate_distance_km(
                profile.latitude,
                profile.longitude,
                city.latitude,
                city.longitude,
            )
            if nearest_distance is None or distance < nearest_distance:
                nearest_city = city
                nearest_distance = distance

        if nearest_city is None:
            continue

        profile.current_city_id = nearest_city.id
        profile.save(update_fields=["current_city"])


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0010_homeowner_profile_location_fields"),
    ]

    operations = [
        migrations.RunPython(
            backfill_handyman_current_city,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
