import json
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from apps.kpi_engine.models import KPIRecord
from apps.financial_system.models import RevenueSnapshot
from apps.subscription_analytics.models import RecurringRevenueMetric

class AdminDashboardFinanceView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Primary mission-control visual suite delivering advanced operational Intelligence.
    """
    template_name = 'dashboard_core/analytics_overview.html'
    
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        try:
             return super().get(request, *args, **kwargs)
        except Exception:
             import traceback
             from django.http import HttpResponse
             return HttpResponse(f"<h1>CRITICAL_DEBUG_CAPTURE</h1><pre>{traceback.format_exc()}</pre>", content_type="text/html", status=500)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        
        # 1. Real-time Cashbox and FX Evaluation
        from apps.financial_conversion.services.cashbox_engine import CashboxAnalyticsEngine
        cash_data = None
        try:
             cash_data = CashboxAnalyticsEngine.calculate_composited_summary()
             context['cashbox'] = cash_data
        except Exception:
             context['cashbox'] = None

        # 2. Retrieve core headline KPIs
        try:
            total_rev = KPIRecord.objects.filter(kpi_key='TOTAL_GROSS').first()
            arpu = KPIRecord.objects.filter(kpi_key='ARPU').first()
            last_rr = RecurringRevenueMetric.objects.first()
            
            context['headline_stats'] = {
                'total_gross': cash_data['composite_totals']['all_usd'] if context.get('cashbox') else (total_rev.value if total_rev else 0),
                'arpu': arpu.value if arpu else 0,
                'mrr': (last_rr.mrr_cents / 100.0) if last_rr else 0,
                'arr': (last_rr.arr_cents / 100.0) if last_rr else 0
            }
        except Exception:
            context['headline_stats'] = {'total_gross':0, 'arpu':0, 'mrr':0, 'arr':0}

        # Chart Data Preparation
        snapshots = RevenueSnapshot.objects.filter(period='daily').order_by('snapshot_date')[:30]
        
        chart_dates = []
        chart_revenue = []
        
        for snap in snapshots:
            chart_dates.append(snap.snapshot_date.strftime("%Y-%m-%d"))
            chart_revenue.append(float(snap.gross_revenue_cents / 100.0))
            
        context['chart_data_json'] = json.dumps({
            'labels': chart_dates,
            'data': chart_revenue
        })
        
        return context

