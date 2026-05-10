import requests
import decimal
from django.utils import timezone
from ..models import ExchangeProvider, ExchangeRate

class BaseExchangeAdapter:
    """ Blueprint for secondary market data ingestion APIs."""
    def get_rate(self, base, quote):
        raise NotImplementedError()

class ExchangeRateHostAdapter(BaseExchangeAdapter):
    def get_rate(self, base, quote):
        # Mock/Real implementation using fallback tolerant pattern
        url = f"https://api.exchangerate.host/convert?from={base}&to={quote}"
        try:
            # Short timeout prevents thread blocking
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return decimal.Decimal(str(data['result']))
        except:
            pass
        return None

class CurrencyServiceOrchestrator:
    """ Handles the cascade logic querying multiple fallback channels."""
    
    ADAPTERS = {
        'exchangerate.host': ExchangeRateHostAdapter(),
    }
    
    @classmethod
    def update_latest_rate(cls, base='USD', quote='SYP'):
        """ Main logical handler iterating configured enabled feeds."""
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
                    return rate_obj
                    
        # If all fail, simply return latest from static history or manual override
        return ExchangeRate.objects.filter(
            base_currency=base, quote_currency=quote
        ).order_by('-valid_from').first()
