import urllib.request
import json
import decimal
from django.utils import timezone
from django.core.cache import cache
from ..models import ExchangeProvider, ExchangeRate

CACHE_TIMEOUT = 900 # 15 mins cache duration

class BaseExchangeAdapter:
    """ Blueprint for secondary market data ingestion APIs."""
    def get_rate(self, base, quote):
        raise NotImplementedError()

class ExchangeRateHostAdapter(BaseExchangeAdapter):
    def get_rate(self, base, quote):
        # Standard library implementation with Zero dependencies
        url = f"https://api.exchangerate.host/convert?from={base}&to={quote}"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    # Fallback handling for structure
                    return decimal.Decimal(str(data.get('result', 0)))
        except Exception:
            pass
        return None


class CurrencyServiceOrchestrator:
    """ Handles the cascade logic querying multiple fallback channels."""
    
    ADAPTERS = {
        'exchangerate.host': ExchangeRateHostAdapter(),
    }
    
    @classmethod
    def update_latest_rate(cls, base='USD', quote='SYP'):
        """ Main logical handler iterating configured enabled feeds with Cache Interception."""
        cache_key = f"fx_rate_{base}_{quote}"
        cached_val = None
        try:
            cached_val = cache.get(cache_key)
        except Exception:
            pass # Redis offline resilience bypass

        if cached_val:
            return cached_val

            
        active_providers = ExchangeProvider.objects.filter(is_enabled=True).order_by('priority')
        
        for p in active_providers:
            adapter = cls.ADAPTERS.get(p.name)
            if adapter:
                val = adapter.get_rate(base, quote)
                if val and val > 0:
                    # Atomic persistence record entry
                    rate_obj = ExchangeRate.objects.create(
                        base_currency=base,
                        quote_currency=quote,
                        rate=val,
                        provider=p
                    )
                    # Warm the cache for next hits
                    try:
                        cache.set(cache_key, rate_obj, CACHE_TIMEOUT)
                    except Exception:
                        pass
                    return rate_obj
                    
        # Fallback retrieval loop
        fallback_rate = ExchangeRate.objects.filter(
            base_currency=base, quote_currency=quote
        ).order_by('-valid_from').first()
        
        if fallback_rate:
            try:
                cache.set(cache_key, fallback_rate, 60) # shorter cache for fallback
            except Exception:
                pass
            
        return fallback_rate


