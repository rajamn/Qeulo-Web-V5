# core/management/commands/toggle_ai.py
# usage python manage.py toggle_ai <hospital_id> <enable/disable>
# usage python manage.py toggle_ai 4 disable

from django.core.management.base import BaseCommand, CommandError
from core.models import Hospital


class Command(BaseCommand):
    help = "Enable or disable AI for a given hospital"

    def add_arguments(self, parser):
        parser.add_argument(
            "hospital_id",
            type=int,
            help="ID of the hospital"
        )

        parser.add_argument(
            "status",
            type=str,
            choices=["true", "false", "enable", "disable"],
            help="Enable (true) or disable (false) AI"
        )

    def handle(self, *args, **options):
        hospital_id = options["hospital_id"]
        status = options["status"].lower()

        # Normalize
        enable_ai = status in ["true", "enable"]

        try:
            hospital = Hospital.objects.get(pk=hospital_id)
        except Hospital.DoesNotExist:
            raise CommandError(f"Hospital ID {hospital_id} does not exist.")

        # Update field
        hospital.ai_enabled = enable_ai
        hospital.save(update_fields=["ai_enabled"])

        self.stdout.write(
            self.style.SUCCESS(
                f"AI {'ENABLED' if enable_ai else 'DISABLED'} for Hospital ID {hospital_id} ({hospital.name})"
            )
        )
