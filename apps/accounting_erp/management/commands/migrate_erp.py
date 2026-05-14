from django.core.management.base import BaseCommand
from apps.accounting_erp.services.legacy_transformer import run_migration

class Command(BaseCommand):
    help = 'Migrates existing sales data to the new Enterprise Accounting System'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initiating ERP Migration...'))
        run_migration()
        self.stdout.write(self.style.SUCCESS('Successfully migrated to the new ERP system.'))
