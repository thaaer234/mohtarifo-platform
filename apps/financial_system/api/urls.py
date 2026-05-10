from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RevenueSnapshotViewSet, FinancialLedgerViewSet, FinancialOperationsViewSet

router = DefaultRouter()
router.register(r'snapshots', RevenueSnapshotViewSet, basename='finance-snapshots')
router.register(r'ledger', FinancialLedgerViewSet, basename='finance-ledger')
router.register(r'ops', FinancialOperationsViewSet, basename='finance-ops')

urlpatterns = [
    path('', include(router.urls)),
]
