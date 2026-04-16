import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0009_guest_location_snapshot"),
        ("jobs", "0027_jobapplication_discount_applied_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="guestlocationsnapshot",
            name="last_location_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="handymanprofile",
            name="current_city",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="handyman_profiles",
                to="jobs.city",
            ),
        ),
        migrations.AddField(
            model_name="handymanprofile",
            name="last_location_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="homeownerprofile",
            name="current_city",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="homeowner_profiles",
                to="jobs.city",
            ),
        ),
        migrations.AddField(
            model_name="homeownerprofile",
            name="last_location_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="homeownerprofile",
            name="latitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="homeownerprofile",
            name="longitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                max_digits=9,
                null=True,
            ),
        ),
    ]
