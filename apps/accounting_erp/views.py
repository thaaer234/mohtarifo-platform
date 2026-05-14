from django.views.generic import TemplateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count
from django.utils import timezone
from .models import Account, JournalEntry, JournalLine, Wallet, Voucher, CommissionRule
from .services.financial_statements import FinancialStatementEngine
from .services.trial_balance import TrialBalanceEngine
from decimal import Decimal

class BaseAccountingView(LoginRequiredMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_accounting_admin'] = self.request.user.is_staff
        return context

class AccountingDashboardView(BaseAccountingView, TemplateView):
    template_name = 'accounting_erp/dashboard_premium.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Performance Data
        pnl = FinancialStatementEngine.generate_income_statement(start_date=month_start)
        bs = FinancialStatementEngine.generate_balance_sheet()
        
        context['kpis'] = {
            'revenue_month': pnl['revenue_total'],
            'deferred_revenue': Account.objects.get(code='2101').get_balance(),
            'teacher_payables': Account.objects.get(code='2201').get_balance(),
            'net_profit': pnl['net_income'],
        }
        
        context['recent_journals'] = JournalEntry.objects.all().order_by('-created_at')[:10]
        context['wallets'] = {
            'total_teacher_balance': Wallet.objects.filter(owner_type='TEACHER').aggregate(total=Sum('balance'))['total'] or 0,
            'total_center_balance': Wallet.objects.filter(owner_type='CENTER').aggregate(total=Sum('balance'))['total'] or 0,
        }
        return context

class IncomeStatementView(BaseAccountingView, TemplateView):
    template_name = 'accounting_erp/income_statement.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report'] = FinancialStatementEngine.generate_income_statement()
        return context

class BalanceSheetView(BaseAccountingView, TemplateView):
    template_name = 'accounting_erp/balance_sheet.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report'] = FinancialStatementEngine.generate_balance_sheet()
        return context

class TrialBalanceView(BaseAccountingView, TemplateView):
    template_name = 'accounting_erp/trial_balance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        engine = TrialBalanceEngine()
        context['report'] = engine.get_report()
        return context

class ChartOfAccountsView(BaseAccountingView, ListView):
    model = Account
    template_name = 'accounting_erp/chart_tree.html'
    context_object_name = 'accounts'
    def get_queryset(self): return Account.objects.all().order_by('code')

class JournalListView(BaseAccountingView, ListView):
    model = JournalEntry
    template_name = 'accounting_erp/journal_list.html'
    context_object_name = 'journals'
    paginate_by = 50

class VoucherDetailView(BaseAccountingView, DetailView):
    model = Voucher
    template_name = 'accounting_erp/voucher_premium.html'
    context_object_name = 'voucher'
