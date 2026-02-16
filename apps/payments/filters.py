import django_filters
from .models import SSLPayment

class SSLPaymentFilter(django_filters.FilterSet):
    created = django_filters.DateFromToRangeFilter()

    class Meta:
        model = SSLPayment
        fields = [
            'transaction_id',
            'status',
            'pay_reason',
            'payer_mobile',
            'payer',
            'gateway_reference',
            'created',
        ]