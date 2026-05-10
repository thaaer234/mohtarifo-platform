from django.utils import timezone
from django.db.models import Sum
from billing.models import Subscription, Plan
from ..models import RecurringRevenueMetric, SubscriptionSnapshot

class SubscriptionAnalyticsService:
    """
    Business engine calculating real-time and snapshot SaaS metrics
    like MRR and Churn rates based on legacy billing states.
    """

    @classmethod
    def calculate_current_mrr_cents(cls):
        """
        Iterates through active subscriptions and normalizes value to monthly amounts.
        Ensures high safety tolerance and direct computation.
        """
        active_subs = Subscription.objects.filter(status='active').select_related('plan')
        
        total_mrr_cents = 0
        for sub in active_subs:
            if not sub.plan:
                continue
            
            period = sub.plan.billing_period.lower()
            amount = sub.plan.price_cents
            
            # Normalize to monthly period
            if 'month' in period or 'monthly' in period:
                total_mrr_cents += amount
            elif 'year' in period or 'annual' in period:
                total_mrr_cents += amount // 12
            elif 'week' in period:
                total_mrr_cents += (amount * 52) // 12
            else:
                # Assume monthly fallback if period not detected
                total_mrr_cents += amount
                
        return total_mrr_cents

    @classmethod
    def capture_nightly_snapshot(cls, record_date=None):
        """
        Persists core subscription metrics to optimized storage for long-term trending.
        """
        if not record_date:
            record_date = timezone.now().date()
            
        mrr = cls.calculate_current_mrr_cents()
        arr = mrr * 12
        
        # Store recurring revenue numbers
        rr_metric, _ = RecurringRevenueMetric.objects.update_or_create(
            metric_date=record_date,
            defaults={
                'mrr_cents': mrr,
                'arr_cents': arr
            }
        )
        
        # Store volume statistics
        total_active = Subscription.objects.filter(status='active').count()
        new_today = Subscription.objects.filter(
            created_at__date=record_date
        ).count()
        
        # Mock churn lookup for sample implementation; in prod we'd scan cancel datetimes
        churn_today = Subscription.objects.filter(
            status='canceled',
            updated_at__date=record_date
        ).count()
        
        # Simple Churn Rate Basis Points Calculation
        churn_rate_bps = 0
        if total_active > 0:
            churn_rate_bps = int((churn_today / total_active) * 10000)
            
        snapshot, _ = SubscriptionSnapshot.objects.update_or_create(
            snapshot_date=record_date,
            defaults={
                'total_active_subscriptions': total_active,
                'new_subscriptions': new_today,
                'canceled_subscriptions': churn_today,
                'churn_rate_bps': churn_rate_bps
            }
        )
        
        return snapshot
