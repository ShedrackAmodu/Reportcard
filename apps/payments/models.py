from model_utils.models import TimeStampedModel
from django.conf import settings
from django.db import models
from django.utils import timezone

from .utils import model_help_texts


class SSLPayment(TimeStampedModel):
    """ Table to store payment records coming from
    admission form.
    Recommended way to create this class's instance is
    only after a successfull admission payment.
    """

    # NOTE: DO NOT CHANGE THE ORDER OF TUPLE ITEMS.
    SSL_PAY_REASONS = (
        ('admission', 'Online Admission'),
        ('midfee', 'Midterm Exam Fee'),
        ('finalfee', 'Final Exam Fee'),
    )
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('success', 'Successful'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    )
    transaction_id = models.PositiveIntegerField()
    gateway_reference = models.CharField(max_length=120, blank=True, null=True, unique=True)
    gateway_name = models.CharField(max_length=30, default='SSLCommerz')
    status = models.CharField(max_length=15, choices=PAYMENT_STATUS, default='pending')
    payer = models.CharField(
        model_help_texts.SSLPAYMENT_PAYER,
        max_length=150
    )
    received_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )
    pay_reason = models.CharField(
        max_length=10,
        choices=SSL_PAY_REASONS
    )
    payer_mobile = models.CharField(max_length=15)
    payer_email = models.EmailField()
    # By 2021, longest city name has 85 chars.
    payer_city = models.CharField(max_length=85)
    payer_country = models.CharField(max_length=55)
    payment_channel = models.CharField(max_length=50, blank=True, null=True)
    verification_notes = models.TextField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='verified_ssl_payments'
    )
    gateway_payload = models.JSONField(blank=True, null=True)

    class Meta:
        verbose_name_plural = model_help_texts.SSLPAYMENT_VERBOSE_NAME_PLURAL
        ordering = ['-created', 'received_amount']
    
    def __str__(self):
        return f'TransID #{self.transaction_id}'

    def mark_as_verified(self, user=None, note=''):
        self.status = 'success'
        self.verified_at = timezone.now()
        self.verified_by = user
        if note:
            self.verification_notes = note
        self.save(update_fields=['status', 'verified_at', 'verified_by', 'verification_notes', 'modified'])


class SSLAdmissionPaymentVerfication(TimeStampedModel):
    VERIFICATION_STATUS = (
        (0, 'Rejected'),
        (1, 'Verfied')
    )
    payment = models.ForeignKey(
        SSLPayment,
        on_delete=models.CASCADE,
        related_name='verfied_payments'
    )
    status = models.PositiveSmallIntegerField(
        choices=VERIFICATION_STATUS,
        default=0
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='admission_pay_verifications',
        null=True
    )

    class Meta:
        verbose_name_plural = model_help_texts.SSAL_ADMISSION_PAYMENT_VERIFICATION_VERBOSE_NAME_PLURAL
        ordering = ['-created', ]
    
    def __str__(self):
        return f'{self.payment} {self.status} by {self.verified_by}'
