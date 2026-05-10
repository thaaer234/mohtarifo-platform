from rest_framework import serializers
from ..models import RevenueSnapshot, FinancialLedger

class RevenueSnapshotSerializer(serializers.ModelSerializer):
    gross_formatted = serializers.SerializerMethodField()
    net_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = RevenueSnapshot
        fields = [
            'id', 'period', 'snapshot_date', 
            'gross_revenue_cents', 'gross_formatted',
            'net_revenue_cents', 'net_formatted', 
            'transaction_count', 'active_customers_count'
        ]
        
    def get_gross_formatted(self, obj):
        return "{:.2f}".format(obj.gross_revenue_cents / 100.0)

    def get_net_formatted(self, obj):
        return "{:.2f}".format(obj.net_revenue_cents / 100.0)

class FinancialLedgerSerializer(serializers.ModelSerializer):
    amount_formatted = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = FinancialLedger
        fields = [
            'id', 'created_at', 'entry_type', 
            'amount_cents', 'amount_formatted', 'currency',
            'external_source', 'username', 'description'
        ]
        
    def get_amount_formatted(self, obj):
        return "{:.2f}".format(obj.amount_cents / 100.0)
