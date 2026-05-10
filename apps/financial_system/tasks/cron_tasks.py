from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task(name='finance.sync_and_aggregate_everything')
def perform_comprehensive_sync():
    """
    Main scheduled coordinator to rebuild reporting data across multiple apps.
    Suggested triggering: Once daily at 1:00 AM.
    """
    yesterday = timezone.now().date() - timezone.timedelta(days=1)
    
    # Phase 1: Ingest legacy into ledger
    from apps.financial_system.services.etl import LedgerSyncService, AnalyticsRollupService
    
    logger.info("Starting phase 1: Ledger Sync")
    synced_count = LedgerSyncService.sync_missing_payments(lookback_days=3)
    logger.info(f"Synced {synced_count} historical payments.")
    
    # Phase 2: Generate snapshots
    AnalyticsRollupService.generate_daily_snapshot(yesterday)
    
    # Phase 3: Subscription Analytics
    from apps.subscription_analytics.services.metrics_engine import SubscriptionAnalyticsService
    SubscriptionAnalyticsService.capture_nightly_snapshot(yesterday)
    
    # Phase 4: Universal KPI Sync
    from apps.kpi_engine.services.aggregator import KPIAggregationService
    KPIAggregationService.run_nightly_sync()
    
    # Phase 5: Predictive Analysis & Forecasting
    from apps.analytics_engine.services.predictor import RevenueForecastingService
    RevenueForecastingService.generate_simple_linear_forecast(horizon_days=30)
    
    # Phase 6: Payment Forensics
    from apps.payment_analytics.services.analyzer import PaymentGatewayAnalyticsService
    PaymentGatewayAnalyticsService.rollup_gateway_metrics(yesterday)
    
    return "Comprehensive Finance Sync Completed Successfully with Forecasting."
