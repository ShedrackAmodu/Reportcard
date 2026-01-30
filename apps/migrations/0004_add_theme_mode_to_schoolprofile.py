"""Add theme_mode field to SchoolProfile.

Generated manually to fix missing column error in SQLite.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apps", "0003_reporttemplate_schoolprofile_reporttemplateusage_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name='schoolprofile',
            name='theme_mode',
            field=models.CharField(
                max_length=20,
                default='light',
                choices=[
                    ('light', 'Light'),
                    ('dark', 'Dark'),
                    ('auto', 'Auto'),
                ],
                help_text='Theme mode for reports and dashboard',
            ),
        ),
    ]
