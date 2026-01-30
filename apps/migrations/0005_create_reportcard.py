# Generated manually to create ReportCard model table
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('apps', '0004_add_theme_mode_to_schoolprofile'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReportCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('academic_year', models.CharField(blank=True, help_text='Academic year (e.g., 2024/2025)', max_length=20)),
                ('average_grade', models.FloatField(blank=True, null=True, help_text='Calculated average grade percentage')),
                ('class_rank', models.PositiveIntegerField(blank=True, null=True, help_text="Student's rank in class")),
                ('status', models.CharField(choices=[('draft','Draft'),('published','Published'),('archived','Archived')], default='draft', max_length=20, db_index=True)),
                ('is_published', models.BooleanField(default=False, db_index=True)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('generated_data', models.JSONField(blank=True, default=dict, help_text='Generated report card data')),
                ('pdf_file', models.FileField(blank=True, help_text='Generated PDF file', null=True, upload_to='report_cards/pdfs/')),
                ('custom_fields_data', models.JSONField(blank=True, default=dict, help_text='Custom field values for this report card')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='report_cards', to='apps.user', db_index=True)),
                ('grading_period', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='report_cards', to='apps.gradingperiod', db_index=True)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='report_cards', to='apps.reporttemplate', db_index=True)),
                ('school', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='apps.school', db_index=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_report_cards', to=settings.AUTH_USER_MODEL)),
                ('published_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='published_report_cards', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('student','grading_period','template')},
            },
        ),
    ]
