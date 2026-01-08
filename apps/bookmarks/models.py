"""
Bookmark models for saving jobs and handymen for later reference.
"""

from django.db import models

from apps.common.models import BaseModel


class JobBookmark(BaseModel):
    """
    Handyman bookmarking a job for later reference.

    A handyman can bookmark jobs they're interested in to easily find them later.
    """

    handyman = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="job_bookmarks",
        help_text="The handyman who bookmarked the job",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="bookmarks",
        help_text="The bookmarked job",
    )

    class Meta:
        db_table = "job_bookmarks"
        unique_together = ("handyman", "job")
        ordering = ["-created_at"]
        verbose_name = "Job Bookmark"
        verbose_name_plural = "Job Bookmarks"

    def __str__(self):
        return f"{self.handyman.email} -> {self.job.title}"


class HandymanBookmark(BaseModel):
    """
    Homeowner bookmarking a handyman for later reference.

    A homeowner can bookmark handymen they're interested in hiring.
    """

    homeowner = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="handyman_bookmarks",
        help_text="The homeowner who bookmarked the handyman",
    )
    handyman_profile = models.ForeignKey(
        "profiles.HandymanProfile",
        on_delete=models.CASCADE,
        related_name="bookmarks",
        help_text="The bookmarked handyman profile",
    )

    class Meta:
        db_table = "handyman_bookmarks"
        unique_together = ("homeowner", "handyman_profile")
        ordering = ["-created_at"]
        verbose_name = "Handyman Bookmark"
        verbose_name_plural = "Handyman Bookmarks"

    def __str__(self):
        return f"{self.homeowner.email} -> {self.handyman_profile.display_name}"
