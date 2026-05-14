from django.db.models import Sum
from decimal import Decimal
from apps.accounting_erp.models import Account, JournalLine, AccountCategory

class TrialBalanceEngine:
    """
    Aggregates current ledger state to produce dynamic balancing sheets.
    """
    @classmethod
    def get_full_trial_balance(cls, start_date=None, end_date=None):
        """
        Computes aggregate debit/credit totals for all accounts for a dynamic period.
        """
        lines = JournalLine.objects.all()
        if start_date:
            lines = lines.filter(journal__posting_date__gte=start_date)
        if end_date:
            lines = lines.filter(journal__posting_date__lte=end_date)
            
        summary = lines.values('account_id').annotate(
            total_dr=Sum('debit_amount'),
            total_cr=Sum('credit_amount')
        )
        
        ledger_map = {str(item['account_id']): item for item in summary}
        accounts = Account.objects.filter(is_group=False).order_by('code')
        
        report = []
        total_net_dr = Decimal('0.00')
        total_net_cr = Decimal('0.00')
        
        for acc in accounts:
            metrics = ledger_map.get(str(acc.id), {'total_dr': Decimal('0'), 'total_cr': Decimal('0')})
            dr = metrics['total_dr'] or Decimal('0')
            cr = metrics['total_cr'] or Decimal('0')
            
            if acc.category in [AccountCategory.ASSET, AccountCategory.EXPENSE]:
                net = dr - cr
                balance_dr = net if net > 0 else Decimal('0')
                balance_cr = abs(net) if net < 0 else Decimal('0')
            else:
                net = cr - dr
                balance_cr = net if net > 0 else Decimal('0')
                balance_dr = abs(net) if net < 0 else Decimal('0')
                
            if dr > 0 or cr > 0:
                report.append({
                    'code': acc.code,
                    'name': acc.name_ar if acc.name_ar else acc.name,
                    'category': acc.get_category_display(),
                    'total_debit': dr,
                    'total_credit': cr,
                    'net_debit': balance_dr,
                    'net_credit': balance_cr
                })
                total_net_dr += dr
                total_net_cr += cr
                
        return {
            'accounts': report,
            'grand_totals': {
                'debit': total_net_dr,
                'credit': total_net_cr,
                'is_balanced': abs(total_net_dr - total_net_cr) < Decimal('0.01')
            }
        }
