from django.core.management.base import BaseCommand
from apps.bunny_analytics.services.integration import BunnyIntegrationService

class Command(BaseCommand):
    help = 'Forces recursive cost re-evaluation against simulated edge dataset.'

    def handle(self, *args, **options):
        self.stdout.write("Triggering Bunny Edge Analytics Simulation...")
        success = BunnyIntegrationService.sync_and_recalculate_costs()
        if success:
            self.stdout.write(self.style.SUCCESS("Successfully materialized detailed cost-per-stream metrics."))
        else:
            self.stdout.write(self.style.ERROR("Sync sequence failed."))
