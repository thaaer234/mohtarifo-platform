from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from apps.accounting_erp.models import Account, JournalEntry
from apps.accounting_erp.services.trial_balance import TrialBalanceEngine

class BaseAccountingView(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

class AccountingDashboardView(BaseAccountingView, TemplateView):
    """ Executive control panel delivering immediate financial liquidity and health visualizers. """
    template_name = 'accounting_erp/dashboard_main.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.accounting_erp.services.financial_statements import FinancialStatementEngine
        from apps.accounting_erp.services.trial_balance import TrialBalanceEngine
        
        # 1. Pull high level aggregates
        pnl = FinancialStatementEngine.generate_income_statement()
        bs = FinancialStatementEngine.generate_balance_sheet()
        
        context['net_income'] = pnl['net_income']
        context['total_revenue'] = pnl['total_revenue']
        
        # 2. Direct specific account extractions (Cash 11, Receivables 12, Payables 21)
        from apps.accounting_erp.models import JournalLine
        from django.db.models import Sum
        from decimal import Decimal
        
        def get_cat_balance(code_prefix):
            agg = JournalLine.objects.filter(account__code__startswith=code_prefix).aggregate(dr=Sum('debit_amount'), cr=Sum('credit_amount'))
            dr = agg['dr'] or Decimal('0')
            cr = agg['cr'] or Decimal('0')
            # Simplify based on typical category start digit (1=Dr normal, 2=Cr normal)
            return (dr - cr) if code_prefix.startswith('1') else (cr - dr)

        context['available_cash'] = get_cat_balance('11') # Assets: Liquid Cash
        context['receivables'] = get_cat_balance('12') # Assets: AR
        context['liabilities'] = get_cat_balance('2')  # All Liabilities
        
        return context


class ChartOfAccountsView(BaseAccountingView, TemplateView):
    """ Displays hierarchical tree map of operational ledger indices. """
    template_name = 'accounting_erp/chart_tree.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from django.db.models import Sum
        from decimal import Decimal
        from apps.accounting_erp.models import JournalLine
        
        # 1. Aggregate line level
        rollup = JournalLine.objects.values('account_id').annotate(dr=Sum('debit_amount'), cr=Sum('credit_amount'))
        balance_map = {str(item['account_id']): (item['dr'] or Decimal(0)) - (item['cr'] or Decimal(0)) for item in rollup}
        
        # 2. Feed accounts list with attached computed balances
        accounts = list(Account.objects.all().order_by('code'))
        
        # Helper to compute balance based on hierarchy later if group? 
        # For simplicity, we attach raw net balance to each direct account object.
        for a in accounts:
            a.raw_balance = balance_map.get(str(a.id), Decimal(0))
            # Format balance logically based on normal category for readability
            if a.category in ['asset', 'expense']:
                 a.display_balance = a.raw_balance
            else:
                 a.display_balance = a.raw_balance * -1 # Flip signs for credit normal accounts
        
        context['accounts'] = accounts
        return context


class JournalVoucherListView(BaseAccountingView, TemplateView):
    """ Consolidated history stream of total balancing system vouchers. """
    template_name = 'accounting_erp/journal_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        acc_filter = self.request.GET.get('account_id')
        qs = JournalEntry.objects.all().order_by('-posting_date')
        
        if acc_filter:
            qs = qs.filter(lines__account_id=acc_filter).distinct()
            from apps.accounting_erp.models import Account
            context['filtered_account'] = Account.objects.filter(pk=acc_filter).first()
            
        context['vouchers'] = qs
        return context

class TrialBalanceReportView(BaseAccountingView, TemplateView):
    """ Official balancing ledger aggregate summation report wrapper. """
    template_name = 'accounting_erp/trial_balance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report'] = TrialBalanceEngine.get_full_trial_balance()
        return context

class IncomeStatementReportView(BaseAccountingView, TemplateView):
    """ Premium formal operational Statement of Activities (Profit & Loss). """
    template_name = 'accounting_erp/income_statement.html'
    
    def get_context_data(self, **kwargs):
        from apps.accounting_erp.services.financial_statements import FinancialStatementEngine
        context = super().get_context_data(**kwargs)
        
        cc_id = self.request.GET.get('cost_center')
        context['pnl'] = FinancialStatementEngine.generate_income_statement(cost_center_id=cc_id)
        
        from apps.accounting_erp.models import CostCenter
        context['cost_centers'] = CostCenter.objects.all()
        context['selected_cc'] = cc_id
        return context

class BalanceSheetReportView(BaseAccountingView, TemplateView):
    """ Static statement measuring snapshot position (Assets = L + E). """
    template_name = 'accounting_erp/balance_sheet.html'
    
    def get_context_data(self, **kwargs):
        from apps.accounting_erp.services.financial_statements import FinancialStatementEngine
        context = super().get_context_data(**kwargs)
        
        cc_id = self.request.GET.get('cost_center')
        context['bs'] = FinancialStatementEngine.generate_balance_sheet(cost_center_id=cc_id)
        
        from apps.accounting_erp.models import CostCenter
        context['cost_centers'] = CostCenter.objects.all()
        context['selected_cc'] = cc_id
        return context


class JournalVoucherDetailView(BaseAccountingView, TemplateView):
    """ Primary precision visual endpoint formatted specifically for physical archival print generation. """
    template_name = 'accounting_erp/voucher_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.shortcuts import get_object_or_404
        from django.db.models import Sum
        from decimal import Decimal
        
        pk = self.kwargs.get('pk')
        voucher = get_object_or_404(JournalEntry, pk=pk)
        lines = voucher.lines.all().select_related('account', 'cost_center').order_by('-debit_amount')
        
        totals = lines.aggregate(dr=Sum('debit_amount'), cr=Sum('credit_amount'))
        
        context['voucher'] = voucher
        context['lines'] = lines
        context['totals'] = {
            'debit': totals['dr'] or Decimal('0'),
            'credit': totals['cr'] or Decimal('0')
        }
        return context

class UniversalErpExcelExportView(BaseAccountingView, TemplateView):
    """ 
    Provides zero-dependency high-speed generation of valid CSV-Excel exports.
    Uses UTF-8-BOM enabling instant seamless reading by Microsoft Excel desktop. 
    """
    def get(self, request, *args, **kwargs):
        import csv
        from django.http import HttpResponse
        
        report_type = kwargs.get('report_type')
        filename = f"erp_export_{report_type}.csv"
        
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Microsoft Excel requires specific signature to read Arabic properly in CSV
        response.write(u'\ufeff'.encode('utf8'))
        
        writer = csv.writer(response)
        
        if report_type == 'trial_balance':
            from apps.accounting_erp.services.trial_balance import TrialBalanceEngine
            data = TrialBalanceEngine.get_full_trial_balance()
            writer.writerow(['دليل الحساب', 'اسم الحساب', 'إجمالي مدين', 'إجمالي دائن', 'صافي مدين', 'صافي دائن'])
            for acc in data['accounts']:
                writer.writerow([acc['code'], acc['name'], acc['total_debit'], acc['total_credit'], acc['net_debit'], acc['net_credit']])
            writer.writerow([])
            writer.writerow(['إجمالي الميزان', '', data['grand_totals']['debit'], data['grand_totals']['credit']])

        elif report_type == 'income_statement':
            from apps.accounting_erp.services.financial_statements import FinancialStatementEngine
            data = FinancialStatementEngine.generate_income_statement()
            writer.writerow(['بند البيان', 'القيمة'])
            writer.writerow(['--- الإيرادات ---', ''])
            for r in data['revenue']:
                writer.writerow([r['name'], r['val']])
            writer.writerow(['إجمالي الإيرادات', data['total_revenue']])
            writer.writerow([])
            writer.writerow(['--- المصروفات ---', ''])
            for e in data['expense']:
                writer.writerow([e['name'], e['val']])
            writer.writerow(['إجمالي المصروفات', data['total_expense']])
            writer.writerow([])
            writer.writerow(['صافي الربح/الخسارة', data['net_income']])

        elif report_type == 'journal':
            writer.writerow(['التاريخ', 'المرجع', 'البيان'])
            for item in JournalEntry.objects.all().order_by('-posting_date'):
                writer.writerow([item.posting_date, item.reference, item.memo])
                
        elif report_type == 'chart':
            writer.writerow(['كود الحساب', 'اسم الحساب', 'النوع', 'رئيسي/فرعي'])
            for acc in Account.objects.all().order_by('code'):
                writer.writerow([acc.code, acc.name, acc.get_category_display(), "رئيسي" if acc.is_group else "فرعي"])

        return response

class RebuildAccountingSystemView(BaseAccountingView, TemplateView):
    """ Administrative tool to perform emergency reconstruction of the accounting dataset from history. """
    def get(self, request, *args, **kwargs):
        from apps.accounting_erp.services.chart_seeder import ChartOfAccountsSeeder
        from apps.accounting_erp.services.legacy_transformer import LegacyAccountingTransformer
        from django.contrib import messages
        from django.shortcuts import redirect
        
        try:
            # 1. Rebuild Chart structure if missing
            ChartOfAccountsSeeder.seed_standard_tree()
            
            # 2. Execute mass transformer from all time history

            msg = LegacyAccountingTransformer.auto_generate_ledger_from_sales()
            messages.success(request, f"تمت المعالجة بنجاح: {msg}")
            
        except Exception as e:
            messages.error(request, f"خطأ أثناء المزامنة: {str(e)}")
            
        return redirect('accounting_erp:chart_tree')




