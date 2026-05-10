import json
from decimal import Decimal
from django.views.generic import TemplateView
from django.utils import timezone
from apps.currency_engine.models import ExchangeRate
from apps.operational_expenses.models import MonthlyBurnRateReport, OperationalExpense
from apps.video_cost_engine.models import VideoCalculatedUnitCost
from django.db.models import Sum

class OperationalAnalyticsView(TemplateView):
    """
    Strategic Control Deck gathering metrics scattered across multi-tier financial 
    sub-systems into unified structural maps for visualization layers.
    """
    template_name = "cost_analysis/ops_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # A. Currency Component
        latest_rate = ExchangeRate.objects.filter(base_currency='USD', quote_currency='SYP').order_by('-valid_from').first()
        context['exchange_rate'] = latest_rate.rate if latest_rate else Decimal('14500.00')
        
        # B. Core Burn Rates
        burn = MonthlyBurnRateReport.objects.first() # Assuming most recent via ordering
        context['burn_metrics'] = {
            'total_usd': burn.composite_burn_total_usd if burn else 0,
            'infra': burn.total_infra_burn_usd if burn else 0,
            'ops': burn.total_operational_burn_usd if burn else 0,
        }
        
        # C. Video Unit Logic
        unit = VideoCalculatedUnitCost.objects.first()
        if unit:
            context['unit_costs'] = {
                'per_vid': unit.cost_per_video_cents / 100.0,
                'per_gb': unit.cost_per_gb_cents / 100.0
            }
        else:
            context['unit_costs'] = {'per_vid': 0.0, 'per_gb': 0.0}
            
        # D. Expense Composition Chart Mapping
        today = timezone.now().date()
        comp_data = list(OperationalExpense.objects.filter(
            transaction_date__year=today.year, 
            transaction_date__month=today.month
        ).values('expense_type').annotate(total=Sum('amount_cents')))
        
        chart_labels = [c['expense_type'] for c in comp_data]
        chart_vals = [float(c['total'])/100.0 for c in comp_data]
        
        # Fallbacks to ensure dynamic UI always renders cleanly on fresh boots
        if not chart_labels:
            chart_labels = ['Staff', 'Marketing', 'Infra', 'API Overhead']
            chart_vals = [4500, 1200, 800, 350]
            
        context['expense_composition_json'] = json.dumps({
            'labels': chart_labels,
            'data': chart_vals
        })
        
        return context
