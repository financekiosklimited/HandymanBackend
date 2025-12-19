# Generated manually to fix unique public_id migration issue

import uuid

from django.db import migrations, models


def generate_unique_public_ids(apps, schema_editor):
    """
    Generate unique public_id values for existing waitlist entries.
    """
    WaitlistEntry = apps.get_model("waitlist", "WaitlistEntry")
    for entry in WaitlistEntry.objects.all():
        entry.public_id = uuid.uuid4()
        entry.save(update_fields=["public_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("waitlist", "0002_alter_waitlistentry_user_type"),
    ]

    operations = [
        # Step 1: Add public_id field without unique constraint
        migrations.AddField(
            model_name="waitlistentry",
            name="public_id",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, null=True
            ),
        ),
        # Step 2: Populate unique values for existing records
        migrations.RunPython(
            generate_unique_public_ids, reverse_code=migrations.RunPython.noop
        ),
        # Step 3: Make field non-nullable and add unique constraint
        migrations.AlterField(
            model_name="waitlistentry",
            name="public_id",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
        # Other field alterations
        migrations.AlterField(
            model_name="waitlistentry",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="waitlistentry",
            name="id",
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="waitlistentry",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
    ]
