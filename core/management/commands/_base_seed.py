# core/management/commands/_base_seed.py
from django.core.management.base import BaseCommand

class BaseSeedCommand(BaseCommand):
    """
    Abstract base for seed commands.
    Subclasses must define:
      - help: str
      - self.seed() to do the work.
    """
    def handle(self, *args, **options):
        # make the options available on self for seed()
        self.options = options

        self.stdout.write(self.style.MIGRATE_HEADING(f"🛠️  Starting {self.help}…"))
        try:
            self.seed()
            self.stdout.write(self.style.SUCCESS(f"✅ {self.help} completed."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error in {self.help}: {e}"))
            raise

        
    def seed(self):
        raise NotImplementedError("Subclasses of BaseSeedCommand must implement .seed()")
