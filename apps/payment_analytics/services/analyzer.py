from django.db.models import Sum, Count
from billing.models import Payment
from ..models import PaymentGatewayMetric

class PaymentGatewayAnalyticsService:
    """
    Calculates operational metadata detailing the efficacy of configured 
    payment providers using decoupled querying techniques.
    """
    
    @classmethod
    def rollup_gateway_metrics(cls, analysis_date):
        """
        Scans legacy transactions categorized by provider string and calculates success ratio.
        """
        base_qs = Payment.objects.filter(created_at__date=analysis_date)
        
        # Extract uniquely active gateways on that day
        gateways = base_qs.values_list('provider', flat=True).distinct()
        
        for gw in gateways:
            if not gw: continue
            
            stats = base_qs.filter(provider=gw).aggregate(
                success_cnt=Count('id', filter=models.Q(status='paid')),
                fail_cnt=Count('id', filter=models.Q(status='failed')),
                success_vol=Sum('amount_cents', filter=models.Q(status='paid')),
                fail_vol=Sum('amount_cents', filter=models.Q(status='failed'))
            )
            
            PaymentGatewayMetric.objects.update_or_create(
                gateway_name=gw,
                metric_date=analysis_date,
                defaults={
                    'successful_count': stats.get('success_cnt') or 0,
                    'failed_count': stats.get('fail_cnt') or 0,
                    'success_volume_cents': stats.get('success_vol') or 0,
                    'failed_volume_cents': stats.get('fail_vol') or 0
                }
            )
            
# Need models imported for models.Q support internally
from django.db import models
