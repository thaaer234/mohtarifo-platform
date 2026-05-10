from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RevenueSnapshotViewSet, FinancialLedgerViewSet

router = DefaultRouter()
router.register(r'snapshots', RevenueSnapshotViewSet, basename='finance-snapshots')
router.register(r'ledger', FinancialLedgerViewSet, basename='finance-ledger')

urlpatterns = [
    path('', include(router.urls)),
]
