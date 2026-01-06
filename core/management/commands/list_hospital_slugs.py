from django.core.management.base import BaseCommand
from core.models import Hospital

class Command(BaseCommand):
    help = "Display all hospital names and their slugs"

    def handle(self, *args, **options):
        hospitals = Hospital.objects.all().order_by("name")
        if not hospitals.exists():
            self.stdout.write(self.style.WARNING("No hospitals found."))
            return

        self.stdout.write(self.style.SUCCESS("🏥 List of hospitals and their slugs:"))
        for h in hospitals:
            self.stdout.write(f" - {h.name} → {h.slug}")
