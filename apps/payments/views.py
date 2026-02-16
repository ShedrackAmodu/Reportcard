from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum
from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin
from django.shortcuts import get_object_or_404, redirect
from .models import SSLPayment
from .tables import SSLPaymentTable
from .filters import SSLPaymentFilter


class DashboardSSLPaymentsList(LoginRequiredMixin, UserPassesTestMixin, SingleTableMixin, FilterView):
    model = SSLPayment
    table_class = SSLPaymentTable
    template_name = 'payments/dashboard/sslpayments.html'
    filterset_class = SSLPaymentFilter
    paginate_by = 25

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.is_staff

    def post(self, request, *args, **kwargs):
        payment_id = request.POST.get('payment_id')
        action = request.POST.get('action')
        note = (request.POST.get('verification_notes') or '').strip()
        payment = get_object_or_404(SSLPayment, pk=payment_id)

        if action == 'verify':
            payment.mark_as_verified(user=request.user, note=note)
            messages.success(request, f'Payment #{payment.transaction_id} verified.')
        elif action == 'reject':
            payment.status = 'failed'
            payment.verification_notes = note
            payment.verified_by = request.user
            payment.save(update_fields=['status', 'verification_notes', 'verified_by', 'modified'])
            messages.warning(request, f'Payment #{payment.transaction_id} marked as failed.')
        return redirect('payments:dashboard_ssl_payments_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        payment_qs = self.filterset.qs if hasattr(self, 'filterset') else self.model.objects.all()
        ctx['payment_stats'] = {
            'total': payment_qs.count(),
            'successful': payment_qs.filter(status='success').count(),
            'pending': payment_qs.filter(status='pending').count(),
            'failed': payment_qs.filter(status='failed').count(),
            'total_value': payment_qs.aggregate(total=Sum('received_amount')).get('total') or 0,
        }
        return ctx

dashboard_ssl_payments_list = DashboardSSLPaymentsList.as_view()