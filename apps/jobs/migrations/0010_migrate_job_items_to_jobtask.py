from django.db import migrations


def forwards(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    JobTask = apps.get_model("jobs", "JobTask")

    tasks_to_create = []
    for job in Job.objects.all().iterator():
        items = job.job_items or []
        if not isinstance(items, list) or len(items) == 0:
            continue
        for idx, title in enumerate(items):
            if not isinstance(title, str):
                continue
            tasks_to_create.append(
                JobTask(
                    job=job,
                    title=title,
                    order=idx,
                )
            )
    if tasks_to_create:
        JobTask.objects.bulk_create(tasks_to_create)


def backwards(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    JobTask = apps.get_model("jobs", "JobTask")

    job_ids = list(JobTask.objects.values_list("job_id", flat=True).distinct())
    for job in Job.objects.filter(id__in=job_ids).iterator():
        task_titles = list(
            JobTask.objects.filter(job=job)
            .order_by("order", "created_at")
            .values_list("title", flat=True)
        )
        job.job_items = task_titles
        job.save(update_fields=["job_items"])

    JobTask.objects.filter(job_id__in=job_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0009_job_assigned_handyman_job_completed_at_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
