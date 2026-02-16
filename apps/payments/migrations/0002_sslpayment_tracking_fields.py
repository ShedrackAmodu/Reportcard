from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='sslpayment',
            name='gateway_name',
            field=models.CharField(default='SSLCommerz', max_length=30),
        ),
        migrations.AddField(
            model_name='sslpayment',
            name='gateway_payload',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sslpayment',
            name='gateway_reference',
            field=models.CharField(blank=True, max_length=120, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='sslpayment',
            name='payment_channel',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='sslpayment',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('success', 'Successful'),
                    ('failed', 'Failed'),
                    ('reversed', 'Reversed'),
                ],
                default='pending',
                max_length=15,
            ),
        ),
        migrations.AddField(
            model_name='sslpayment',
            name='verification_notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sslpayment',
            name='verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sslpayment',
            name='verified_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='verified_ssl_payments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

