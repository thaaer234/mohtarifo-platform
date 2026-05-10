from decimal import Decimal
from django.db.models import Sum
from apps.infrastructure_finance.models import InfrastructureExpense
from ..models import VideoSystemSnapshot, VideoCalculatedUnitCost

class VideoCostLogicEngine:
    """
    Strategic algorithmic processor fusing machine overhead data pools 
    with binary payload volumes to determine per-node profit integrity.
    """
    
    @classmethod
    def compute_unit_costs(cls, snapshot_date):
        """
        Cross-joins infrastructure summation with volume counts for specific snapshot.
        """
        try:
            snap = VideoSystemSnapshot.objects.get(capture_date=snapshot_date)
        except VideoSystemSnapshot.DoesNotExist:
            return None
            
        # 1. Aggregated infrastructure pools related specifically to video logic (cdn, storage, hosting)
        total_infra_pool = InfrastructureExpense.objects.filter(
            category__in=['hosting', 'cdn', 'storage', 'bandwidth']
        ).aggregate(tot=Sum('monthly_cost_usd_cents'))['tot'] or 0
        
        # Handle zero divisor guards safety
        vid_count = max(Decimal('1'), Decimal(snap.total_video_count))
        gb_count = max(Decimal('1'), Decimal(snap.total_storage_gb))
        min_count = max(Decimal('1'), Decimal(snap.total_duration_minutes))
        
        # Convert integer pool into decimal for float math safety
        pool_dec = Decimal(total_infra_pool)
        
        # Unitary Calculation outcomes
        c_vid = pool_dec / vid_count
        c_gb = pool_dec / gb_count
        c_min = pool_dec / min_count
        
        # Atomic persistence update
        metric, _ = VideoCalculatedUnitCost.objects.update_or_create(
            snapshot=snap,
            defaults={
                'cost_per_gb_cents': c_gb,
                'cost_per_video_cents': c_vid,
                'cost_per_minute_cents': c_min,
                'total_monthly_infrastructure_burn_cents': int(pool_dec)
            }
        )
        return metric
