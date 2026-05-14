from decimal import Decimal
from django.db.models import Sum
from apps.accounting_erp.models import Account, JournalLine, AccountCategory

class FinancialStatementEngine:
    """
    Synthesizes raw Trial Balance aggregates into formal standardized reporting layouts.
    """
    
    @classmethod
    def generate_income_statement(cls, cost_center_id=None, start_date=None, end_date=None):
        """
        Produces Revenues vs Expenses grid resulting in Net Profit / Loss.
        """
        lines = JournalLine.objects.all()
        if cost_center_id:
            lines = lines.filter(cost_center_id=cost_center_id)
            
        if start_date:
            lines = lines.filter(journal__posting_date__gte=start_date)
        if end_date:
            lines = lines.filter(journal__posting_date__lte=end_date)

        revenue_accs = Account.objects.filter(category=AccountCategory.REVENUE, is_group=False)
        expense_accs = Account.objects.filter(category=AccountCategory.EXPENSE, is_group=False)
        
        total_rev = Decimal('0')
        rev_lines = []
        for acc in revenue_accs:
            agg = lines.filter(account=acc).aggregate(dr=Sum('debit_amount'), cr=Sum('credit_amount'))
            net = (agg['cr'] or Decimal('0')) - (agg['dr'] or Decimal('0'))
            if net != 0:
                rev_lines.append({'name': acc.display_name, 'val': net})
                total_rev += net
                
        total_exp = Decimal('0')
        exp_lines = []
        for acc in expense_accs:
            agg = lines.filter(account=acc).aggregate(dr=Sum('debit_amount'), cr=Sum('credit_amount'))
            net = (agg['dr'] or Decimal('0')) - (agg['cr'] or Decimal('0'))
            if net != 0:
                exp_lines.append({'name': acc.display_name, 'val': net})
                total_exp += net
                
        net_income = total_rev - total_exp
        
        return {
            'revenue': rev_lines,
            'total_revenue': total_rev,
            'expense': exp_lines,
            'total_expense': total_exp,
            'net_income': net_income,
            'is_profit': net_income >= 0
        }

    @classmethod
    def generate_balance_sheet(cls, cost_center_id=None, end_date=None):
        """
        Analyzes cumulative static standing (Assets = Liabilities + Equity).
        """
        lines = JournalLine.objects.all()
        if cost_center_id:
            lines = lines.filter(cost_center_id=cost_center_id)
        if end_date:
            lines = lines.filter(journal__posting_date__lte=end_date)

        def get_grouped_accounts(category, normal_dr=True):
            accs = Account.objects.filter(category=category, is_group=False)
            total = Decimal('0')
            items = []
            for acc in accs:
                agg = lines.filter(account=acc).aggregate(dr=Sum('debit_amount'), cr=Sum('credit_amount'))
                dr = agg['dr'] or Decimal('0')
                cr = agg['cr'] or Decimal('0')
                net = (dr - cr) if normal_dr else (cr - dr)
                if net != 0:
                    items.append({'name': acc.display_name, 'val': net})
                    total += net
            return items, total
            
        assets_list, total_assets = get_grouped_accounts(AccountCategory.ASSET, normal_dr=True)
        liab_list, total_liab = get_grouped_accounts(AccountCategory.LIABILITY, normal_dr=False)
        equity_list, total_equity = get_grouped_accounts(AccountCategory.EQUITY, normal_dr=False)
        
        pnl = cls.generate_income_statement(cost_center_id=cost_center_id, end_date=end_date)
        curr_net = pnl['net_income']
        adjusted_total_equity = total_equity + curr_net
        
        return {
            'assets': assets_list,
            'total_assets': total_assets,
            'liabilities': liab_list,
            'total_liabilities': total_liab,
            'equity': equity_list,
            'total_equity_static': total_equity,
            'current_profit': curr_net,
            'total_equity_final': adjusted_total_equity,
            'total_liab_equity': total_liab + adjusted_total_equity,
            'is_balanced': abs(total_assets - (total_liab + adjusted_total_equity)) < Decimal('0.01')
        }
