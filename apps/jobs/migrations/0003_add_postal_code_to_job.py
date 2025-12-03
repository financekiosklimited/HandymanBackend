# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0002_rename_estimated_budget_per_hour_to_estimated_budget'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='postal_code',
            field=models.CharField(blank=True, max_length=7),
        ),
    ]
