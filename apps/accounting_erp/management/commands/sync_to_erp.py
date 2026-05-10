from django.core.management.base import BaseCommand
from apps.accounting_erp.services.legacy_transformer import LegacyAccountingTransformer

class Command(BaseCommand):
    help = 'Reads legacy sales and builds automatic balanced double-entries in the ERP.'

    def handle(self, *args, **options):
        self.stdout.write("Starting Automated Legacy-to-ERP Postings Transformer...")
        result = LegacyAccountingTransformer.auto_generate_ledger_from_sales()
        self.stdout.write(self.style.SUCCESS(result))
