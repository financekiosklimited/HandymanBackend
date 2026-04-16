"""Profile-related business logic services."""

import math

from apps.jobs.models import City


class ProfileLocationService:
    """Service for resolving profile-related location data."""

    def resolve_nearest_city(self, latitude, longitude):
        """Return the nearest active city for the given coordinates."""
        if latitude is None or longitude is None:
            return None

        nearest_city = None
        nearest_distance = None

        cities = City.objects.filter(
            is_active=True,
            latitude__isnull=False,
            longitude__isnull=False,
        )

        for city in cities:
            distance = self._calculate_distance_km(
                latitude,
                longitude,
                city.latitude,
                city.longitude,
            )
            if nearest_distance is None or distance < nearest_distance:
                nearest_city = city
                nearest_distance = distance

        return nearest_city

    def _calculate_distance_km(
        self,
        latitude,
        longitude,
        city_latitude,
        city_longitude,
    ):
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


profile_location_service = ProfileLocationService()
