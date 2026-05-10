from django.db.models import Q, Sum
from billing.models import Payment, Subscription, CoursePurchase, AccessCode

class LegacyPaymentSelector:
    """
    Decoupled read-only layer extracting payment primitives 
    from existing billing.Payment without exposing business logic.
    """
    
    @staticmethod
    def get_successful_payments_range(start_date, end_date):
        """Fetches verified payments in defined datetime bracket."""
        return Payment.objects.filter(
            status='paid',
            created_at__gte=start_date,
            created_at__lte=end_date
        ).select_related('user')

    @staticmethod
    def aggregate_total_revenue_in_range(start_date, end_date):
        """Performs safe server-side aggregation on legacy schema."""
        result = Payment.objects.filter(
            status='paid',
            created_at__gte=start_date,
            created_at__lte=end_date
        ).aggregate(total=Sum('amount_cents'))
        
        return result.get('total') or 0

    @staticmethod
    def get_access_code_sales_range(start_date, end_date):
        """Extracts finalized offline voucher instrument transactions."""
        return AccessCode.objects.filter(
            sale_status='sold',
            sold_at__gte=start_date,
            sold_at__lte=end_date
        ).select_related('sold_by', 'course', 'package')

class LegacySubscriptionSelector:
    """Adaptation interface for core subscription schema analytics."""
    
    @staticmethod
    def count_active_subscriptions():
        return Subscription.objects.filter(status='active').count()
        
    @staticmethod
    def get_churned_count(start_date, end_date):
        return Subscription.objects.filter(
            status='canceled',
            updated_at__gte=start_date,
            updated_at__lte=end_date
        ).count()
