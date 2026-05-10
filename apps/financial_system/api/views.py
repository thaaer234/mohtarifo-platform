from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import RevenueSnapshot, FinancialLedger
from ..serializers.financial_serializers import RevenueSnapshotSerializer, FinancialLedgerSerializer

class RevenueSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint delivering pre-aggregated revenue metrics ideal for rendering charts.
    """
    queryset = RevenueSnapshot.objects.all().order_by('-snapshot_date')
    serializer_class = RevenueSnapshotSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['period']
    
    @action(detail=False, methods=['get'], url_path='latest-overview')
    def latest_overview(self, request):
        """Custom RPC style aggregation returning today's summary statistics."""
        from django.db.models import Sum
        total = RevenueSnapshot.objects.aggregate(total_net=Sum('net_revenue_cents'))
        
        # Just returning raw aggregation for dashboard rapid usage
        return Response({
            "lifetime_net_cents": total.get('total_net') or 0,
            "currency": "USD",
            "data_points": self.queryset.count()
        })

class FinancialLedgerViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Auditable ledger trail browser. Allows auditing exact transactional operations.
    """
    queryset = FinancialLedger.objects.all().select_related('user')
    serializer_class = FinancialLedgerSerializer
    permission_classes = [IsAdminUser]
    ordering_fields = ['created_at', 'amount_cents']
    search_fields = ['description', 'external_reference_id', 'user__username']


class FinancialOperationsViewSet(viewsets.ViewSet):
    """
    Command and control triggers delivering operational orchestration APIs.
    """
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['post'], url_path='trigger-sync')
    def trigger_sync(self, request):
        """ Forces an on-demand pull from legacy data repositories."""
        from apps.financial_system.services.etl import LedgerSyncService
        count = LedgerSyncService.sync_missing_payments(lookback_days=30)
        return Response({
            "status": "success",
            "message": f"Synchronized {count} legacy transactions into the isolated ledger.",
            "synced_count": count
        })
        
    @action(detail=False, methods=['get'], url_path='cashbox-liquidity')
    def cashbox_liquidity(self, request):
        """ Evaluates enterprise-wide reserves against current live pricing."""
        from apps.financial_conversion.services.cashbox_engine import CashboxAnalyticsEngine
        payload = CashboxAnalyticsEngine.calculate_composited_summary()
        return Response(payload)

    @action(detail=False, methods=['get'], url_path='live-fx-rate')
    def live_fx_rate(self, request):
        """ Reads current dynamic currency index via cache-interception."""
        from apps.currency_engine.services.api_adapter import CurrencyServiceOrchestrator
        rate_obj = CurrencyServiceOrchestrator.update_latest_rate('USD', 'SYP')
        return Response({
            "base": "USD", "quote": "SYP",
            "rate": str(rate_obj.rate) if rate_obj else "N/A",
            "timestamp": rate_obj.valid_from if rate_obj else None
        })

