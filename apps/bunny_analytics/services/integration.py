from decimal import Decimal
from django.db.models import Count
from ..models import BunnyRateConfiguration, BunnyVideoAnalytics, BunnyPlatformReport

class BunnyIntegrationService:
    """
    External bridge extracting raw video stream metrics and injecting calculated 
    operational multipliers based on configurable price-per-GB schemas.
    """
    
    @classmethod
    def sync_and_recalculate_costs(cls):
        """ Orchestrates external fetch then local algebraic recalculation cascade."""
        # 1. Retrieve Active Rate context
        rates = BunnyRateConfiguration.objects.filter(is_active=True).first()
        if not rates:
            # Generate safe static defaults to prevent zero failure
            rates = BunnyRateConfiguration.objects.create()
            
        # 2. Fetch from Bunny.net Video API (Simulated realistic endpoint query)
        # NOTE: Typically iterates /library/{LibID}/videos endpoint
        raw_videos_payload = cls._fetch_simulated_bunny_payload()
        
        total_vids = len(raw_videos_payload)
        if total_vids == 0: return False
        
        # Calculate distributed fixed infrastructure fee share per asset
        vps_monthly_usd = Decimal(rates.monthly_vps_cost_cents) / Decimal('100.0')
        infra_share_per_vid = vps_monthly_usd / Decimal(total_vids)
        
        # 3. Loop & Calculate each node
        for item in raw_videos_payload:
            b_id = item['guid']
            
            size_gb = Decimal(item['storageSize']) / Decimal(1024**3)
            bw_gb = Decimal(item['views'] * (item['storageSize'] * 0.8)) / Decimal(1024**3) # rough approximation derived from views
            dur_mins = Decimal(item['length']) / Decimal(60)
            
            # Apply standard variables
            storage_c = size_gb * Decimal(str(rates.price_per_gb_storage))
            bw_c = bw_gb * Decimal(str(rates.price_per_gb_bandwidth))
            enc_c = dur_mins * Decimal(str(rates.encoding_per_min))
            
            # Composite formula application
            total_cost = storage_c + bw_c + enc_c + infra_share_per_vid
            
            BunnyVideoAnalytics.objects.update_or_create(
                bunny_id=b_id,
                defaults={
                    'title': item.get('title', 'Untitled Stream'),
                    'storage_size_bytes': item['storageSize'],
                    'bandwidth_used_bytes': int(bw_gb * (1024**3)),
                    'duration_seconds': item['length'],
                    'total_views': item['views'],
                    'calculated_total_cost_usd': total_cost
                }
            )
            
        return True

    @classmethod
    def _fetch_simulated_bunny_payload(cls):
        """ Simulates structure typically returned by Bunny's pull-zone analytic API."""
        import random
        results = []
        for i in range(1, 20):
            results.append({
                'guid': f"bunny-vid-x{1000 + i}",
                'title': f"Advanced Lesson Module {i}",
                'storageSize': random.randint(500000000, 2500000000), # 500MB - 2.5GB
                'length': random.randint(900, 3600), # 15min - 60min
                'views': random.randint(50, 1200)
            })
        return results
