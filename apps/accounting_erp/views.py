from django.views.generic import TemplateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .models import Account, JournalEntry, CostCenter
from .services.trial_balance import TrialBalanceEngine
from .services.excel_engine import HighQualityExcelExporter

class BaseAccountingView(LoginRequiredMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_accounting_admin'] = self.request.user.is_staff
        return context

class AccountingDashboardView(BaseAccountingView, TemplateView):
    template_name = 'accounting_erp/dashboard_main.html'

class TrialBalanceView(BaseAccountingView, TemplateView):
    template_name = 'accounting_erp/trial_balance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        engine = TrialBalanceEngine()
        context['data'] = engine.get_report()
        return context

from django.views import View

class ExportTrialBalanceExcelView(BaseAccountingView, View):
    def get(self, request, *args, **kwargs):
        engine = TrialBalanceEngine()
        data = engine.get_report()
        exporter = HighQualityExcelExporter()
        return exporter.export_trial_balance(data)

class VoucherPrintView(BaseAccountingView, DetailView):
    model = JournalEntry
    template_name = 'accounting_erp/voucher_print.html'
    context_object_name = 'voucher'

class ChartOfAccountsView(BaseAccountingView, ListView):
    model = Account
    template_name = 'accounting_erp/chart_tree.html'
    context_object_name = 'accounts'
    
    def get_queryset(self):
        return Account.objects.filter(parent=None)

class JournalListView(BaseAccountingView, ListView):
    model = JournalEntry
    template_name = 'accounting_erp/journal_list.html'
    context_object_name = 'vouchers'
    paginate_by = 50
