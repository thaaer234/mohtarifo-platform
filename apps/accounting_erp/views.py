from django.views.generic import TemplateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count
from django.utils import timezone
from .models import Account, JournalEntry, JournalLine, Wallet, Voucher, CommissionRule
from .services.financial_statements import FinancialStatementEngine
from .services.trial_balance import TrialBalanceEngine
from decimal import Decimal

from .models.goals import FinancialGoal

class BaseAccountingView(LoginRequiredMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_accounting_admin'] = getattr(self.request.user, 'is_staff', False)
        return context

class AccountingDashboardView(BaseAccountingView, TemplateView):
    template_name = 'accounting_erp/dashboard_premium.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Performance Data
        try:
            pnl = FinancialStatementEngine.generate_income_statement(start_date=month_start)
        except Exception:
            pnl = {'revenue_total': 0, 'net_income': 0}

        def get_bal(code):
            acc = Account.objects.filter(code=code).first()
            return acc.get_balance() if acc else Decimal('0.00')
        
        context['kpis'] = {
            'revenue_month': pnl.get('revenue_total', 0),
            'deferred_revenue': get_bal('2101'),
            'teacher_payables': get_bal('2201'),
            'net_profit': pnl.get('net_income', 0),
            'liquidity_status': 'healthy',
            'growth_rate': 14.2 # Placeholder for now
        }
        
        cash_bal = get_bal('1101')
        if cash_bal < context['kpis']['teacher_payables']:
            context['kpis']['liquidity_status'] = 'critical'
            
        # Daily Revenue (Last 7 Days)
        daily_revenue = []
        for i in range(6, -1, -1):
            date = today - timezone.timedelta(days=i)
            rev = JournalLine.objects.filter(
                journal__posting_date=date,
                account__code__startswith='4' # Revenue accounts
            ).aggregate(total=Sum('credit_amount'))['total'] or 0
            daily_revenue.append({
                'day': date.strftime('%a'),
                'val': float(rev)
            })

        context['daily_revenue'] = daily_revenue
        context['forecast'] = FinancialStatementEngine.generate_forecast()
        context['active_goals'] = FinancialGoal.objects.filter(is_active=True)
        
        context['recent_journals'] = JournalEntry.objects.all().order_by('-created_at')[:12]
        context['wallets_summary'] = {
            'teacher': Wallet.objects.filter(owner_type='TEACHER').aggregate(total=Sum('balance'))['total'] or 0,
            'center': Wallet.objects.filter(owner_type='CENTER').aggregate(total=Sum('balance'))['total'] or 0,
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
    context_object_name = 'vouchers'
    paginate_by = 50

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from billing.models import SalesCenter
        context['cost_centers'] = SalesCenter.objects.filter(is_active=True)
        return context

class VoucherDetailView(BaseAccountingView, DetailView):
    model = Voucher
    template_name = 'accounting_erp/voucher_premium.html'
    context_object_name = 'voucher'
