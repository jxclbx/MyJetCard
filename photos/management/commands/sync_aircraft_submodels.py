from django.core.management.base import BaseCommand

from photos.services import rebuild_aircraft_variants
from photos.models import AircraftSubModel


class Command(BaseCommand):
    help = "Rebuild the model-submodel lookup table from existing Photo rows."

    def handle(self, *args, **options):
        rebuild_aircraft_variants()
        total = AircraftSubModel.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Synced {total} model-submodel pairs."))
