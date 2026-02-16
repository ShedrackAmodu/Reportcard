from django.contrib import admin
from .models import SSLPayment, SSLAdmissionPaymentVerfication


@admin.register(SSLPayment)
class SSLPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id',
        'gateway_reference',
        'status',
        'payer',
        'received_amount',
        'pay_reason',
        'payer_mobile',
        'payer_email',
        'verified_by',
        'verified_at',
    )
    list_filter = ('status', 'pay_reason', 'gateway_name')
    search_fields = ('transaction_id', 'gateway_reference', 'payer', 'payer_mobile', 'payer_email')


@admin.register(SSLAdmissionPaymentVerfication)
class SSLAdmissionPaymentVerficationAdmin(admin.ModelAdmin):
    list_display = (
        'payment',
        'status',
        'verified_by',
    )
