"""
Serializers for bookmark endpoints.
"""

from rest_framework import serializers

from apps.common.serializers import (
    create_list_response_serializer,
    create_response_serializer,
)
from apps.jobs.models import Job
from apps.jobs.serializers import HandymanForYouJobSerializer
from apps.profiles.models import HandymanProfile
from apps.profiles.serializers import HomeownerHandymanListSerializer

from .models import HandymanBookmark, JobBookmark

# ======================
# Job Bookmark Serializers (for Handyman)
# ======================


class JobBookmarkCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a job bookmark.
    """

    job_id = serializers.UUIDField(
        required=True,
        help_text="Public ID of the job to bookmark",
    )

    def validate_job_id(self, value):
        """Validate that the job exists and is open."""
        try:
            job = Job.objects.get(public_id=value)
            # Only allow bookmarking open jobs
            if job.status != "open":
                raise serializers.ValidationError("Only open jobs can be bookmarked.")
            return job
        except Job.DoesNotExist:
            raise serializers.ValidationError("Job not found.")

    def create(self, validated_data):
        """Create the job bookmark."""
        job = validated_data["job_id"]
        handyman = self.context["request"].user

        # Check if already bookmarked
        bookmark, created = JobBookmark.objects.get_or_create(
            handyman=handyman,
            job=job,
        )
        return bookmark


class JobBookmarkSerializer(serializers.ModelSerializer):
    """
    Serializer for job bookmark detail.
    """

    job = HandymanForYouJobSerializer(read_only=True)

    class Meta:
        model = JobBookmark
        fields = [
            "public_id",
            "job",
            "created_at",
        ]
        read_only_fields = fields


class BookmarkedJobListSerializer(HandymanForYouJobSerializer):
    """
    Serializer for listing bookmarked jobs.
    Extends HandymanForYouJobSerializer to include all job details.
    Adds bookmarked_at field to show when the job was bookmarked.
    """

    bookmarked_at = serializers.DateTimeField(
        read_only=True,
        help_text="When the job was bookmarked",
    )

    class Meta(HandymanForYouJobSerializer.Meta):
        fields = HandymanForYouJobSerializer.Meta.fields + ["bookmarked_at"]


# ======================
# Handyman Bookmark Serializers (for Homeowner)
# ======================


class HandymanBookmarkCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a handyman bookmark.
    """

    handyman_id = serializers.UUIDField(
        required=True,
        help_text="Public ID of the handyman profile to bookmark",
    )

    def validate_handyman_id(self, value):
        """Validate that the handyman exists and is visible."""
        try:
            handyman_profile = HandymanProfile.objects.get(
                public_id=value,
                is_approved=True,
                is_active=True,
            )
            return handyman_profile
        except HandymanProfile.DoesNotExist:
            raise serializers.ValidationError("Handyman not found.")

    def create(self, validated_data):
        """Create the handyman bookmark."""
        handyman_profile = validated_data["handyman_id"]
        homeowner = self.context["request"].user

        # Check if already bookmarked
        bookmark, created = HandymanBookmark.objects.get_or_create(
            homeowner=homeowner,
            handyman_profile=handyman_profile,
        )
        return bookmark


class HandymanBookmarkSerializer(serializers.ModelSerializer):
    """
    Serializer for handyman bookmark detail.
    """

    handyman_profile = HomeownerHandymanListSerializer(read_only=True)

    class Meta:
        model = HandymanBookmark
        fields = [
            "public_id",
            "handyman_profile",
            "created_at",
        ]
        read_only_fields = fields


class BookmarkedHandymanListSerializer(HomeownerHandymanListSerializer):
    """
    Serializer for listing bookmarked handymen.
    Extends HomeownerHandymanListSerializer to include all handyman details.
    Adds bookmarked_at field to show when the handyman was bookmarked.
    """

    bookmarked_at = serializers.DateTimeField(
        read_only=True,
        help_text="When the handyman was bookmarked",
    )

    class Meta(HomeownerHandymanListSerializer.Meta):
        fields = HomeownerHandymanListSerializer.Meta.fields + ["bookmarked_at"]


# ======================
# Response Envelope Serializers
# ======================

# Job Bookmark responses
JobBookmarkResponseSerializer = create_response_serializer(
    JobBookmarkSerializer, "JobBookmarkResponse"
)

BookmarkedJobListResponseSerializer = create_list_response_serializer(
    BookmarkedJobListSerializer, "BookmarkedJobListResponse"
)

# Handyman Bookmark responses
HandymanBookmarkResponseSerializer = create_response_serializer(
    HandymanBookmarkSerializer, "HandymanBookmarkResponse"
)

BookmarkedHandymanListResponseSerializer = create_list_response_serializer(
    BookmarkedHandymanListSerializer, "BookmarkedHandymanListResponse"
)
