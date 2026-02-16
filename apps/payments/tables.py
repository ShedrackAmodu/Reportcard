import django_tables2 as tables
from .models import (
    SSLAdmissionPaymentVerfication, 
    SSLPayment
)


class SSLPaymentTable(tables.Table):
    class Meta:
        model  = SSLPayment
        template_name = 'django_tables2/bootstrap-responsive.html'
        fields = (
            'created',
            'transaction_id',
            'gateway_reference',
            'status',
            'payer',
            'received_amount',
            'pay_reason',
            'payer_mobile',
            'payer_city',
            'verified_by',
            'verified_at',
        )