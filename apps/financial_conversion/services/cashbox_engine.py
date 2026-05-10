from decimal import Decimal
from django.db.models import Sum
from apps.financial_system.models import FinancialLedger
from apps.currency_engine.services.api_adapter import CurrencyServiceOrchestrator

class CashboxAnalyticsEngine:
    """
    Central intelligence core calculating cross-currency valuations
    based on ledger residuals and live marketplace spot rates.
    """
    
    @classmethod
    def calculate_composited_summary(cls):
        """
        Gathers standard balances grouped by recorded currencies, 
        aggregating them into single consolidated denominations.
        """
        
        # 1. Fetch current operational rate from Cache/API
        live_fx = CurrencyServiceOrchestrator.update_latest_rate('USD', 'SYP')
        rate = live_fx.rate if live_fx else Decimal('14800.00')
        
        # 2. Resolve raw Ledger sums by Currency
        totals = FinancialLedger.objects.values('currency').annotate(
            raw_cents=Sum('amount_cents')
        )
        
        balances = {
            'USD': Decimal('0.00'),
            'SYP': Decimal('0.00')
        }
        
        for item in totals:
            cur = item['currency'].upper()
            val_usd = Decimal(item['raw_cents']) / Decimal('100.0')
            balances[cur] = val_usd
            
        usd_reserve = balances.get('USD', Decimal('0'))
        syp_reserve = balances.get('SYP', Decimal('0'))
        
        # 3. Composite Conversion Algebra
        # Value of ALL funds projected entirely into USD
        if rate > 0:
            composite_usd = usd_reserve + (syp_reserve / rate)
        else:
            composite_usd = usd_reserve

        # Value of ALL funds projected entirely into SYP
        composite_syp = (usd_reserve * rate) + syp_reserve

        
        return {
            'reserves': {
                'usd': usd_reserve,
                'syp': syp_reserve
            },
            'composite_totals': {
                'all_usd': composite_usd,
                'all_syp': composite_syp
            },
            'active_rate': rate,
            'rate_timestamp': live_fx.valid_from if live_fx else None
        }
