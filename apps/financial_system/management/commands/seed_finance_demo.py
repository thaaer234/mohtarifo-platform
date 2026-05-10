import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.financial_system.models import RevenueSnapshot
from apps.subscription_analytics.models import RecurringRevenueMetric
from apps.kpi_engine.models import KPIRecord

class Command(BaseCommand):
    help = 'Populates synthetic mock data to showcase visual capabilities of the enterprise finance suite.'

    def handle(self, *args, **options):
        self.stdout.write("Initializing analytic seed process...")
        
        today = timezone.now().date()
        
        # Generate 30 Days of randomized trend data
        base_rev = 500000  # $5000
        
        RevenueSnapshot.objects.all().delete()
        RecurringRevenueMetric.objects.all().delete()
        KPIRecord.objects.all().delete()

        for i in range(30, -1, -1):
            date = today - timezone.timedelta(days=i)
            daily_fluctuation = random.randint(-50000, 80000)
            
            val = base_rev + daily_fluctuation + (i * 2000) # slightly upward trend simulation
            
            RevenueSnapshot.objects.create(
                period='daily',
                snapshot_date=date,
                gross_revenue_cents=val,
                net_revenue_cents=int(val * 0.85),
                transaction_count=random.randint(10, 50),
                active_customers_count=150 + (30-i)
            )
            
            # Simple synthetic MRR growing step by step
            mrr = 1500000 + (30-i) * 50000
            
            RecurringRevenueMetric.objects.create(
                metric_date=date,
                mrr_cents=mrr,
                arr_cents=mrr * 12
            )
            
        # Final Master KPIs for the header stats
        KPIRecord.objects.create(
            kpi_key='TOTAL_GROSS',
            record_date=today,
            display_name='Total Revenue',
            value=Decimal('15420.50'),
            unit='USD'
        )
        
        KPIRecord.objects.create(
            kpi_key='ARPU',
            record_date=today,
            display_name='ARPU',
            value=Decimal('85.60'),
            unit='USD'
        )
        
        self.stdout.write(self.style.SUCCESS("Analytics sandbox seeding completed successfully. Visit dashboard now."))
