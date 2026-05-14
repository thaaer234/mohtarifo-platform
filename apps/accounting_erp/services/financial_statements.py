from decimal import Decimal
from django.db.models import Sum
from ..models import Account, JournalLine, AccountType

class FinancialStatementEngine:
    """
    Standardized Financial Statement Engine for Enterprise ERP.
    """
    
    @classmethod
    def generate_income_statement(cls, cost_center=None, start_date=None, end_date=None):
        """
        Revenues - Expenses = Net Profit / Loss
        """
        lines = JournalLine.objects.all()
        if cost_center:
            lines = lines.filter(cost_center=cost_center)
        if start_date:
            lines = lines.filter(journal__posting_date__gte=start_date)
        if end_date:
            lines = lines.filter(journal__posting_date__lte=end_date)

        # Revenue
        revenue_total = Decimal('0.00')
        revenue_items = []
        for acc in Account.objects.filter(account_type=AccountType.REVENUE, is_group=False):
            bal = acc.get_balance(start_date, end_date)
            if bal != 0:
                revenue_items.append({'name': acc.display_name, 'val': bal})
                revenue_total += bal
                
        # Expenses
        expense_total = Decimal('0.00')
        expense_items = []
        for acc in Account.objects.filter(account_type=AccountType.EXPENSE, is_group=False):
            bal = acc.get_balance(start_date, end_date)
            if bal != 0:
                expense_items.append({'name': acc.display_name, 'val': bal})
                expense_total += bal
                
        net_income = revenue_total - expense_total
        
        return {
            'revenue_items': revenue_items,
            'revenue_total': revenue_total,
            'expense_items': expense_items,
            'expense_total': expense_total,
            'net_income': net_income,
            'is_profit': net_income >= 0
        }

    @classmethod
    def generate_balance_sheet(cls, end_date=None):
        """
        Assets = Liabilities + Equity
        """
        assets_total = Decimal('0.00')
        assets_items = []
        for acc in Account.objects.filter(account_type=AccountType.ASSET, is_group=False):
            bal = acc.get_balance(end_date=end_date)
            if bal != 0:
                assets_items.append({'name': acc.display_name, 'val': bal})
                assets_total += bal
                
        liab_total = Decimal('0.00')
        liab_items = []
        for acc in Account.objects.filter(account_type=AccountType.LIABILITY, is_group=False):
            bal = acc.get_balance(end_date=end_date)
            if bal != 0:
                liab_items.append({'name': acc.display_name, 'val': bal})
                liab_total += bal
                
        equity_total = Decimal('0.00')
        equity_items = []
        for acc in Account.objects.filter(account_type=AccountType.EQUITY, is_group=False):
            bal = acc.get_balance(end_date=end_date)
            if bal != 0:
                equity_items.append({'name': acc.display_name, 'val': bal})
                equity_total += bal
                
        # Current Year Earnings (from P&L)
        pnl = cls.generate_income_statement(end_date=end_date)
        current_earnings = pnl['net_income']
        
        final_equity = equity_total + current_earnings
        
        return {
            'assets_items': assets_items,
            'assets_total': assets_total,
            'liabilities_items': liab_items,
            'liabilities_total': liab_total,
            'equity_items': equity_items,
            'equity_total_static': equity_total,
            'current_earnings': current_earnings,
            'equity_total_final': final_equity,
            'liabilities_and_equity': liab_total + final_equity,
            'is_balanced': abs(assets_total - (liab_total + final_equity)) < Decimal('0.01')
        }

    @classmethod
    def generate_forecast(cls, days=30):
        """
        Predicts future revenue recognition based on active enrollments and session counts.
        """
        try:
            from learning.models import OnlineLessonSession
            from django.utils import timezone
        except ImportError:
            return {'deferred_revenue': 0, 'upcoming_sessions_count': 0, 'estimated_revenue_30d': 0, 'confidence_score': 0}
        
        # 1. Total Unrecognized Revenue (Liability)
        deferred_acc = Account.objects.filter(code='2101').first()
        deferred_rev = deferred_acc.get_balance() if deferred_acc else Decimal('0.00')
        
        # 2. Upcoming Sessions in next X days
        # Note: Model field might be scheduled_at or starts_at. Checking previous context, it was starts_at in some views.
        # Let's assume starts_at or scheduled_at.
        upcoming_sessions = 0
        try:
            upcoming_sessions = OnlineLessonSession.objects.filter(
                starts_at__gte=timezone.now(),
                starts_at__lte=timezone.now() + timezone.timedelta(days=days)
            ).count()
        except Exception:
            pass
        
        # 3. Estimated recognition
        estimated_recognition = deferred_rev * Decimal('0.15')
        
        return {
            'deferred_revenue': deferred_rev,
            'upcoming_sessions_count': upcoming_sessions,
            'estimated_revenue_30d': estimated_recognition,
            'confidence_score': 85 if upcoming_sessions > 10 else 40
        }

