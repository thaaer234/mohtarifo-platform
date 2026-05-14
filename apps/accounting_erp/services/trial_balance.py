from django.db.models import Sum
from decimal import Decimal
from apps.accounting_erp.models import Account, JournalLine

class TrialBalanceEngine:
    def get_report(self, start_date=None, end_date=None):
        accounts = Account.objects.all().order_by('code')
        report = []
        
        # Pre-fetch balances for speed
        lines = JournalLine.objects.all()
        if start_date: lines = lines.filter(journal__posting_date__gte=start_date)
        if end_date: lines = lines.filter(journal__posting_date__lte=end_date)
        
        balance_map = {}
        aggs = lines.values('account_id').annotate(dr=Sum('debit_amount'), cr=Sum('credit_amount'))
        for a in aggs:
            balance_map[a['account_id']] = {'dr': a['dr'] or 0, 'cr': a['cr'] or 0}

        for acc in accounts:
            b = balance_map.get(acc.id, {'dr': 0, 'cr': 0})
            dr = Decimal(str(b['dr']))
            cr = Decimal(str(b['cr']))
            net = dr - cr if acc.account_type in ['ASSET', 'EXPENSE'] else cr - dr
            
            report.append({
                'id': acc.id,
                'code': acc.code,
                'name': acc.display_name,
                'type': acc.get_account_type_display(),
                'debit': dr,
                'credit': cr,
                'net': net,
                'is_group': acc.is_group
            })
            
        return report
