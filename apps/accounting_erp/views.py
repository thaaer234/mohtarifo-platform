from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils import timezone
from datetime import datetime
from apps.accounting_erp.models import Account, JournalEntry
from apps.accounting_erp.services.trial_balance import TrialBalanceEngine

def parse_date_safe(date_str):
    if not date_str: return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        return None

class BaseAccountingView(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

class PrintReportMixin:
    """ Dynamically alternates to a optimized print template if requested. """
    print_template_name = None
    
    def get_template_names(self):
        if self.request.GET.get('format') == 'print' and self.print_template_name:
            return [self.print_template_name]
        return super().get_template_names()

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

class QuickTransactionView(BaseAccountingView, TemplateView):
    """ Simplified gateway enabling non-accountants to record daily cash movements without understanding double-entry. """
    template_name = 'accounting_erp/quick_transaction.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.accounting_erp.models import CostCenter
        context['centers'] = CostCenter.objects.filter(code__startswith='CEN-')
        context['instructors'] = CostCenter.objects.filter(code__startswith='INS-')
        return context

    def post(self, request, *args, **kwargs):
        from decimal import Decimal
        from django.shortcuts import redirect
        from django.contrib import messages
        from django.utils import timezone
        from apps.accounting_erp.models import JournalEntry, JournalLine, Account, CostCenter, AccountCategory
        
        tx_type = request.POST.get('tx_type') # 'collect' or 'pay'
        amount = Decimal(request.POST.get('amount', '0'))
        target_cc_id = request.POST.get('target_cc')
        notes = request.POST.get('notes', '')
        
        if amount <= 0 or not target_cc_id:
            messages.error(request, "خطأ: يجب إدخال المبلغ واختيار الطرف.")
            return redirect('accounting_erp:quick_tx')
            
        try:
            cc = CostCenter.objects.get(pk=target_cc_id)
            cash_acc, _ = Account.objects.get_or_create(code='1101', defaults={'name': 'الصندوق الرئيسي', 'category': AccountCategory.ASSET, 'parent': Account.objects.get(code='1')})
            
            voucher = JournalEntry.objects.create(
                posting_date=timezone.now().date(),
                reference=f"QUICK_{int(timezone.now().timestamp())}",
                memo=f"{'تحصيل نقدية' if tx_type=='collect' else 'صرف دفعة'} - {cc.name} | {notes}"
            )
            
            if tx_type == 'collect':
                # Collecting from Center: Debit Cash, Credit Center Receivable
                recv_acc, _ = Account.objects.get_or_create(code='1201', defaults={'name': 'ذمم مراكز بيع مدينة', 'category': AccountCategory.ASSET, 'parent': Account.objects.get(code='1')})
                JournalLine.objects.create(journal=voucher, account=cash_acc, debit_amount=amount, line_memo="استلام نقدية صندوق")
                JournalLine.objects.create(journal=voucher, account=recv_acc, credit_amount=amount, cost_center=cc, line_memo="تسوية عهدة")
                messages.success(request, f"✅ تم بنجاح تسجيل استلام {amount} من {cc.name}")
                
            elif tx_type == 'pay':
                # Paying Instructor: Debit Liability, Credit Cash
                liab_acc, _ = Account.objects.get_or_create(code='2101', defaults={'name': 'مستحقات المدرسين', 'category': AccountCategory.LIABILITY, 'parent': Account.objects.get(code='2')})
                JournalLine.objects.create(journal=voucher, account=liab_acc, debit_amount=amount, cost_center=cc, line_memo="سداد استحقاق مدرس")
                JournalLine.objects.create(journal=voucher, account=cash_acc, credit_amount=amount, line_memo="صرف نقدي من الصندوق")
                messages.success(request, f"✅ تم بنجاح تسجيل صرف {amount} للمدرس {cc.name}")

        except Exception as e:
            messages.error(request, f"فشل العملية: {str(e)}")
            
        return redirect('accounting_erp:quick_tx')

class ChartOfAccountsView(BaseAccountingView, PrintReportMixin, TemplateView):
    """ Displays hierarchical tree map of operational ledger indices. """
    template_name = 'accounting_erp/chart_tree.html'
    print_template_name = 'accounting_erp/chart_tree_print.html'
    
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


class JournalVoucherListView(BaseAccountingView, PrintReportMixin, TemplateView):
    """ Consolidated history stream of total balancing system vouchers. """
    template_name = 'accounting_erp/journal_list.html'
    print_template_name = 'accounting_erp/journal_list_print.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        acc_filter = self.request.GET.get('account_id')
        cc_filter = self.request.GET.get('cost_center_id')
        s_date = parse_date_safe(self.request.GET.get('start_date'))
        e_date = parse_date_safe(self.request.GET.get('end_date'))
        
        qs = JournalEntry.objects.all().order_by('-posting_date')
        
        if s_date:
            qs = qs.filter(posting_date__gte=s_date)
        if e_date:
            qs = qs.filter(posting_date__lte=e_date)
            
        if acc_filter:
            from apps.accounting_erp.models import Account
            target_acc = Account.objects.filter(pk=acc_filter).first()
            context['filtered_account'] = target_acc
            
            if target_acc:
                if target_acc.is_group:
                    qs = qs.filter(lines__account__code__startswith=target_acc.code)
                else:
                    qs = qs.filter(lines__account=target_acc)

        if cc_filter:
            qs = qs.filter(lines__cost_center_id=cc_filter)
            from apps.accounting_erp.models import CostCenter
            context['filtered_cc'] = CostCenter.objects.filter(pk=cc_filter).first()
            
        qs = qs.distinct()
        
        from apps.accounting_erp.models import CostCenter
        context['cost_centers'] = CostCenter.objects.all() # Keep all, maybe paginate later if huge

            
        context['vouchers'] = qs
        context['start_date'] = s_date
        context['end_date'] = e_date
        
        # CUMULATIVE RUNNING BALANCE LOGIC (If filtering by Account OR CostCenter)
        if (acc_filter and target_acc) or (cc_filter and context.get('filtered_cc')):
            from django.db.models import Sum
            from decimal import Decimal
            from apps.accounting_erp.models import JournalLine
            
            base_lines = JournalLine.objects.all()
            
            # Apply Account filter if set
            if acc_filter and target_acc:
                if target_acc.is_group:
                    base_lines = base_lines.filter(account__code__startswith=target_acc.code)
                else:
                    base_lines = base_lines.filter(account=target_acc)
            
            # Apply Dimension Filter if set
            if cc_filter:
                base_lines = base_lines.filter(cost_center_id=cc_filter)
                
            # 1. Calculate Opening Balance
            opening_dr = 0
            opening_cr = 0
            if s_date:
                agg_pre = base_lines.filter(journal__posting_date__lt=s_date).aggregate(dr=Sum('debit_amount'), cr=Sum('credit_amount'))
                opening_dr = agg_pre['dr'] or Decimal(0)
                opening_cr = agg_pre['cr'] or Decimal(0)
            
            # Determine normal side: default to DR normal unless targeted acc specifically is credit normal
            is_dr_normal = True
            if target_acc and target_acc.category not in ['asset', 'expense']:
                is_dr_normal = False
                
            def get_net(d, c): return (d - c) if is_dr_normal else (c - d)
            
            running_bal = get_net(opening_dr, opening_cr)
            context['opening_balance'] = running_bal
            
            # 2. Chronological stream
            timeframe_qs = base_lines.order_by('journal__posting_date', 'journal__created_at').select_related('journal')
            if s_date: timeframe_qs = timeframe_qs.filter(journal__posting_date__gte=s_date)
            if e_date: timeframe_qs = timeframe_qs.filter(journal__posting_date__lte=e_date)
            
            narrative_lines = []
            for line in timeframe_qs:
                net_eff = get_net(line.debit_amount or 0, line.credit_amount or 0)
                running_bal += net_eff
                line.running_balance = running_bal
                narrative_lines.append(line)
                
            context['ledger_narrative'] = narrative_lines

            
        return context




class TrialBalanceReportView(BaseAccountingView, PrintReportMixin, TemplateView):
    """ Official balancing ledger aggregate summation report wrapper. """
    template_name = 'accounting_erp/trial_balance.html'
    print_template_name = 'accounting_erp/trial_balance_print.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        s_date = parse_date_safe(self.request.GET.get('start_date'))
        e_date = parse_date_safe(self.request.GET.get('end_date'))
        
        context['report'] = TrialBalanceEngine.get_full_trial_balance(start_date=s_date, end_date=e_date)
        context['start_date'] = s_date
        context['end_date'] = e_date
        return context


class IncomeStatementReportView(BaseAccountingView, PrintReportMixin, TemplateView):
    """ Premium formal operational Statement of Activities (Profit & Loss). """
    template_name = 'accounting_erp/income_statement.html'
    print_template_name = 'accounting_erp/income_statement_print.html'
    
    def get_context_data(self, **kwargs):
        from apps.accounting_erp.services.financial_statements import FinancialStatementEngine
        context = super().get_context_data(**kwargs)
        
        cc_id = self.request.GET.get('cost_center')
        s_date = parse_date_safe(self.request.GET.get('start_date'))
        e_date = parse_date_safe(self.request.GET.get('end_date'))
        
        context['pnl'] = FinancialStatementEngine.generate_income_statement(
            cost_center_id=cc_id, start_date=s_date, end_date=e_date
        )
        
        from apps.accounting_erp.models import CostCenter
        context['cost_centers'] = CostCenter.objects.all()
        context['selected_cc'] = cc_id
        context['start_date'] = s_date
        context['end_date'] = e_date
        return context


class BalanceSheetReportView(BaseAccountingView, PrintReportMixin, TemplateView):
    """ Static statement measuring snapshot position (Assets = L + E). """
    template_name = 'accounting_erp/balance_sheet.html'
    print_template_name = 'accounting_erp/balance_sheet_print.html'
    
    def get_context_data(self, **kwargs):
        from apps.accounting_erp.services.financial_statements import FinancialStatementEngine
        context = super().get_context_data(**kwargs)
        
        cc_id = self.request.GET.get('cost_center')
        e_date = parse_date_safe(self.request.GET.get('end_date'))
        
        context['bs'] = FinancialStatementEngine.generate_balance_sheet(
            cost_center_id=cc_id, end_date=e_date
        )
        
        from apps.accounting_erp.models import CostCenter
        context['cost_centers'] = CostCenter.objects.all()
        context['selected_cc'] = cc_id
        context['end_date'] = e_date
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

class CostCenterAnalysisView(BaseAccountingView, TemplateView):
    template_name = 'accounting_erp/cost_center_analysis.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.accounting_erp.models import CostCenter
        from django.utils import timezone
        import datetime

        # Dates from query params
        start_str = self.request.GET.get('start_date')
        end_str = self.request.GET.get('end_date')
        
        if start_str: start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d').date()
        else: start_date = timezone.now().date().replace(day=1)
        
        if end_str: end_date = datetime.datetime.strptime(end_str, '%Y-%m-%d').date()
        else: end_date = timezone.now().date()

        centers = CostCenter.objects.filter(is_active=True).order_by('code')
        analysis_data = []
        
        t_rev = Decimal('0')
        t_exp = Decimal('0')

        for cc in centers:
            rev = cc.get_total_revenue(start_date, end_date)
            exp = cc.get_total_expenses(start_date, end_date)
            analysis_data.append({
                'code': cc.code,
                'name': cc.name,
                'type': cc.cost_center_type or 'عام',
                'revenue': rev,
                'expenses': exp,
                'net': rev - exp
            })
            t_rev += rev
            t_exp += exp

        context.update({
            'analysis_data': analysis_data,
            'start_date': start_date,
            'end_date': end_date,
            'totals': {
                'total_revenue': t_rev,
                'total_expenses': t_exp,
                'total_instructor_share': 0, 
                'total_net': t_rev - t_exp
            }
        })
        return context


class RebuildAccountingSystemView(BaseAccountingView, TemplateView):
    """أداة إدارية لإعادة بناء كامل البيانات المحاسبية من السجلات التاريخية."""
    def get(self, request, *args, **kwargs):
        from apps.accounting_erp.services.chart_seeder import ChartOfAccountsSeeder
        from apps.accounting_erp.services.legacy_transformer import LegacyAccountingTransformer
        from django.contrib import messages
        from django.shortcuts import redirect

        force = request.GET.get('force', '') == '1'

        try:
            seed_msg = ChartOfAccountsSeeder.seed_standard_tree()
            result   = LegacyAccountingTransformer.run_full_migration(force_rebuild=force)
            messages.success(request, f"✅ {seed_msg} | {result}")
        except Exception as e:
            import traceback
            messages.error(request, f"❌ خطأ أثناء المزامنة: {e}\n{traceback.format_exc()[:500]}")

        return redirect('accounting_erp:chart_tree')




