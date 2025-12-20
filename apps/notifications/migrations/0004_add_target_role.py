# Generated migration for adding target_role to notifications

from django.db import migrations, models


def delete_all_notifications(apps, schema_editor):
    """Delete all existing notifications before adding non-nullable field."""
    Notification = apps.get_model("notifications", "Notification")
    Notification.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0003_broadcastnotification_target_users_and_more"),
    ]

    operations = [
        # Delete all existing notifications first
        migrations.RunPython(delete_all_notifications, migrations.RunPython.noop),
        # Add target_role field (non-nullable since we cleared data)
        migrations.AddField(
            model_name="notification",
            name="target_role",
            field=models.CharField(
                choices=[("handyman", "Handyman"), ("homeowner", "Homeowner")],
                db_index=True,
                max_length=20,
                help_text="Target role for this notification",
            ),
        ),
        # Remove old index
        migrations.RemoveIndex(
            model_name="notification",
            name="notificatio_user_id_611c58_idx",
        ),
        # Add new indexes
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["user", "target_role", "-created_at"],
                name="notificatio_user_id_target_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["target_role"], name="notificatio_target_idx"),
        ),
    ]
