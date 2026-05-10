from django.core.management.base import BaseCommand
from apps.currency_engine.models import ExchangeRate, ExchangeProvider
from decimal import Decimal

class Command(BaseCommand):
    help = 'Authoritative administrative override fixing current active spot rates.'
    
    def add_arguments(self, parser):
        parser.add_argument('rate', type=float, help='Value of 1 USD in SYP')

    def handle(self, *args, **options):
        rate_val = Decimal(str(options['rate']))
        
        # Get or create an explicit override provider
        prov, _ = ExchangeProvider.objects.get_or_create(
            name='Admin Manual Override',
            defaults={'priority': 0, 'is_enabled': True}
        )
        
        # Enforce priority 0 so it always overrides APIs
        prov.priority = 0
        prov.is_enabled = True
        prov.save()
        
        # Atomic write
        new_rate = ExchangeRate.objects.create(
            base_currency='USD',
            quote_currency='SYP',
            rate=rate_val,
            provider=prov
        )
        
        # Force clear redis cache so website updates immediately
        from django.core.cache import cache
        cache.delete("fx_rate_USD_SYP")
        
        self.stdout.write(self.style.SUCCESS(f"Authoritative spot rate locked at 1 USD = {rate_val} SYP successfully."))
