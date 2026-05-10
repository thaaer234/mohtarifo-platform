import decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.currency_engine.models import ExchangeRate, ExchangeProvider
from apps.infrastructure_finance.models import InfrastructureExpense
from apps.video_cost_engine.models import VideoSystemSnapshot
from apps.video_cost_engine.services.math_engine import VideoCostLogicEngine
from apps.operational_expenses.models import OperationalExpense
from apps.operational_expenses.services.burn_engine import BurnRateOrchestrator

class Command(BaseCommand):
    help = 'Pre-populates hyper-realistic operational finance data pools.'

    def handle(self, *args, **options):
        self.stdout.write("Simulating Operational Intelligence Bootstrap...")
        
        # 1. Feed Exchange Engine
        p, _ = ExchangeProvider.objects.get_or_create(name='System Default Seeder')
        ExchangeRate.objects.create(
            provider=p,
            base_currency='USD',
            quote_currency='SYP',
            rate=decimal.Decimal('14850.00')
        )
        
        # 2. Formulate Recurring Infra (e.g. AWS + Bunny CDN)
        InfrastructureExpense.objects.all().delete()
        
        InfrastructureExpense.objects.create(
            category='cdn', vendor_name='Bunny.net Video', 
            monthly_cost_usd_cents=25000, billing_cycle_start=timezone.now().date()
        )
        InfrastructureExpense.objects.create(
            category='hosting', vendor_name='AWS EC2 Cluster', 
            monthly_cost_usd_cents=42000, billing_cycle_start=timezone.now().date()
        )
        
        # 3. Create Binary Video Snapshot (simulate 2,500 videos @ 500GB)
        today = timezone.now().date()
        VideoSystemSnapshot.objects.all().delete()
        snap = VideoSystemSnapshot.objects.create(
            capture_date=today,
            total_video_count=2500,
            total_storage_gb=decimal.Decimal('850.00'),
            total_duration_minutes=45000
        )
        
        # 4. Trigger Algorithmic Calculation cascade
        VideoCostLogicEngine.compute_unit_costs(today)
        
        # 5. Inject High-Level Ops (Staff & Marketing)
        OperationalExpense.objects.all().delete()
        
        OperationalExpense.objects.create(
            expense_type='staff', label='Core Dev Payroll',
            amount_cents=350000, transaction_date=today
        )
        OperationalExpense.objects.create(
            expense_type='marketing', label='Social Reach Campaign',
            amount_cents=75000, transaction_date=today
        )
        
        # 6. Finalize Aggregate Monthly Burn registry
        BurnRateOrchestrator.calculate_monthly_reconciliation(today)
        
        self.stdout.write(self.style.SUCCESS("Operational control deck now active and calibrated."))
