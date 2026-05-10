from decimal import Decimal
from django.db.models import Sum
from apps.accounting_erp.models import Account, JournalLine

class FinancialStatementEngine:
    """
    Synthesizes raw Trial Balance aggregates into formal standardized reporting layouts.
    """
    
    @classmethod
    def generate_income_statement(cls):
        """
        Produces Revenues vs Expenses grid resulting in Net Profit / Loss.
        """
        # Fetch direct aggregates
        lines = JournalLine.objects.all()
        
        revenue_accs = Account.objects.filter(category='revenue', is_group=False)
        expense_accs = Account.objects.filter(category='expense', is_group=False)
        
        total_rev = Decimal('0')
        rev_lines = []
        for acc in revenue_accs:
            agg = lines.filter(account=acc).aggregate(dr=Sum('debit_amount'), cr=Sum('credit_amount'))
            # Revenue is CR normal
            net = (agg['cr'] or Decimal('0')) - (agg['dr'] or Decimal('0'))
            if net != 0:
                rev_lines.append({'name': acc.name, 'val': net})
                total_rev += net
                
        total_exp = Decimal('0')
        exp_lines = []
        for acc in expense_accs:
            agg = lines.filter(account=acc).aggregate(dr=Sum('debit_amount'), cr=Sum('credit_amount'))
            # Expense is DR normal
            net = (agg['dr'] or Decimal('0')) - (agg['cr'] or Decimal('0'))
            if net != 0:
                exp_lines.append({'name': acc.name, 'val': net})
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
