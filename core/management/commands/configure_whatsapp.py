# whatsapp_notifications/management/commands/configure_whatsapp.py
from django.core.management.base import BaseCommand, CommandError
from core.models import Hospital
from whatsapp_notifications.models import WhatsappConfig

# python manage.py configure_whatsapp --hospital-id=5 --enable
# python manage.py configure_whatsapp --hospital-id=5 --disable
# python manage.py configure_whatsapp --hospital-id=5 --enable --no-followup



class Command(BaseCommand):
    help = "Enable or disable WhatsApp communication for a hospital"

    def add_arguments(self, parser):
        parser.add_argument("--hospital-id", type=int, required=True,
                            help="Hospital ID to configure")
        parser.add_argument("--enable", action="store_true",
                            help="Enable WhatsApp communication")
        parser.add_argument("--disable", action="store_true",
                            help="Disable WhatsApp communication")

        # Optional toggles
        parser.add_argument("--no-registration", action="store_true",
                            help="Disable registration confirmations")
        parser.add_argument("--no-reschedule", action="store_true",
                            help="Disable reschedule notifications")
        parser.add_argument("--no-followup", action="store_true",
                            help="Disable follow-up reminders")

    def handle(self, *args, **options):
        hospital_id = options["hospital_id"]
        try:
            hospital = Hospital.objects.get(id=hospital_id)
        except Hospital.DoesNotExist:
            raise CommandError(f"Hospital {hospital_id} not found")

        config, created = WhatsappConfig.objects.get_or_create(hospital=hospital)

        if options["enable"]:
            config.active = True
        if options["disable"]:
            config.active = False

        # Update optional toggles
        if options["no_registration"]:
            config.send_on_registration = False
        if options["no_reschedule"]:
            config.send_reschedules = False
        if options["no_followup"]:
            config.send_followups = False

        config.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"WhatsApp config updated for hospital {hospital.name} "
                f"(Active: {config.active}, "
                f"Registration: {config.send_on_registration}, "
                f"Reschedules: {config.send_reschedules}, "
                f"Follow-ups: {config.send_followups})"
            )
        )
