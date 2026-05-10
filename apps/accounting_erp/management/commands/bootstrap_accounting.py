from django.core.management.base import BaseCommand
from apps.accounting_erp.services.chart_seeder import ChartOfAccountsSeeder

class Command(BaseCommand):
    help = 'Generates full Standardized Arabic Chart of Accounts for LMS.'

    def handle(self, *args, **options):
        self.stdout.write("Bootstrapping LMS Chart of Accounts...")
        result = ChartOfAccountsSeeder.seed_standard_tree()
        self.stdout.write(self.style.SUCCESS(result))
