from django.db import migrations


def set_legacy_exempt_for_existing_jobs(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    Job.objects.all().update(payment_mode="legacy_exempt")


def noop_reverse(apps, schema_editor):
    """No reverse data migration for payment mode backfill."""


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0024_job_payment_mode_jobdispute_financial_action_error_and_more"),
    ]

    operations = [
        migrations.RunPython(
            set_legacy_exempt_for_existing_jobs,
            reverse_code=noop_reverse,
        ),
    ]
