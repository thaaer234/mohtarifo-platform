from django.test import TestCase
from django.utils import timezone
from apps.financial_system.models import FinancialLedger, RevenueSnapshot
from apps.financial_system.services.etl import AnalyticsRollupService

class FinancialSystemTestCase(TestCase):
    """
    Structural regression validation asserting isolated analytic reliability.
    """
    
    def test_ledger_creation_standard(self):
        """Asserts atomic ledger accepts creation and defaults properly."""
        entry = FinancialLedger.objects.create(
            entry_type='revenue',
            amount_cents=5000,
            currency='USD',
            description='Standard Regression Verification'
        )
        assert entry.amount_cents == 5000
        assert entry.id is not None # UUID Auto Gen check
        assert str(entry.currency) == 'USD'
        
    def test_analytic_rollup_service(self):
        """Assures rollup mathematics are correctly aggregate derived from ledger rows."""
        today = timezone.now().date()
        
        # Fabricate dummy input transactions
        FinancialLedger.objects.create(entry_type='revenue', amount_cents=1000, created_at=timezone.now())
        FinancialLedger.objects.create(entry_type='revenue', amount_cents=2500, created_at=timezone.now())
        
        # Run explicit service activation
        snap = AnalyticsRollupService.generate_daily_snapshot(today)
        
        assert snap is not None
        assert snap.gross_revenue_cents == 3500
        assert snap.transaction_count == 2
        
        # Verify model retrieval idempotent guarantee
        re_fetched = RevenueSnapshot.objects.get(snapshot_date=today)
        assert re_fetched.gross_revenue_cents == 3500
