# Generated migration for adding active_role field to User model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_add_is_dummy'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='active_role',
            field=models.CharField(
                blank=True,
                choices=[('admin', 'Admin'), ('handyman', 'Handyman'), ('homeowner', 'Homeowner')],
                db_index=True,
                help_text='Currently active role for the user',
                max_length=20,
                null=True,
            ),
        ),
    ]
