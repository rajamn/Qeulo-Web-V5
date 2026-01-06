from django.core.management.base import BaseCommand, CommandError
from core.models import Hospital
from whatsapp_notifications.models import WhatsappTemplate


# python manage.py set_whatsapp_template --hospital-id=3 --list
# WhatsApp templates for hospital 'City Clinic':
#  - confirmation: appointment_confirmation_city → https://bothook.io/v1/public/triggers/123-confirm
#  - reschedule: appointment_reschedule_city → https://bothook.io/v1/public/triggers/123-resch
#  - followup: followup_reminder_city → https://bothook.io/v1/public/triggers/123-fu

# WhatsApp templates for hospital 'City Clinic':
#  - confirmation: appointment_confirmation_city → https://bothook.io/v1/public/triggers/123-confirm
#  - reschedule: appointment_reschedule_city → https://bothook.io/v1/public/triggers/123-resch
#  - followup: followup_reminder_city → https://bothook.io/v1/public/triggers/123-fu

# python manage.py set_whatsapp_config \
#   --hospital-id=3 \
#   --type=confirmation \
#   --template-name="appointment_confirmation_city" \
#   --webhook-url="https://bothook.io/v1/public/triggers/123-confirm"


class Command(BaseCommand):
    help = "Upsert WhatsApp template + webhook for a hospital, or list/delete current config"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hospital-id",
            type=int,
            required=True,
            help="ID of the hospital",
        )
        parser.add_argument(
            "--type",
            type=str,
            choices=["confirmation", "reschedule", "followup"],
            help="Template type (confirmation | reschedule | followup)",
        )
        parser.add_argument(
            "--template-name",
            type=str,
            help="DoubleTick-approved template name",
        )
        parser.add_argument(
            "--webhook-url",
            type=str,
            help="Webhook URL for this template type",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List current WhatsApp template config for the hospital",
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete template config for the given hospital and type",
        )

    def handle(self, *args, **options):
        hospital_id = options["hospital_id"]

        try:
            hospital = Hospital.objects.get(id=hospital_id)
        except Hospital.DoesNotExist:
            raise CommandError(f"Hospital with id {hospital_id} does not exist")

        # 🔹 List mode
        if options["list"]:
            templates = WhatsappTemplate.objects.filter(hospital=hospital)
            if not templates.exists():
                self.stdout.write(self.style.WARNING(
                    f"No WhatsApp templates configured for hospital '{hospital.hospital_name}'"
                ))
                return

            self.stdout.write(self.style.SUCCESS(
                f"WhatsApp templates for hospital '{hospital.hospital_name}':"
            ))
            for tpl in templates:
                self.stdout.write(
                    f" - {tpl.template_type}: {tpl.template_name} → {tpl.webhook_url or '(no webhook set)'}"
                )
            return

        tpl_type = options.get("type")

        # 🔹 Delete mode
        if options["delete"]:
            if not tpl_type:
                raise CommandError("You must provide --type when using --delete")

            deleted, _ = WhatsappTemplate.objects.filter(
                hospital=hospital,
                template_type=tpl_type
            ).delete()

            if deleted:
                self.stdout.write(self.style.SUCCESS(
                    f"Deleted {tpl_type} template for hospital '{hospital.hospital_name}'"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"No {tpl_type} template found for hospital '{hospital.hospital_name}'"
                ))
            return

        # 🔹 Upsert mode
        tpl_name = options.get("template_name")
        webhook_url = options.get("webhook_url")

        if not (tpl_type and tpl_name and webhook_url):
            raise CommandError(
                "When not using --list or --delete, you must provide --type, --template-name, and --webhook-url"
            )

        # 🚨 Check for duplicate webhook URL across hospitals
        existing = WhatsappTemplate.objects.filter(
            webhook_url=webhook_url
        ).exclude(hospital=hospital)
        if existing.exists():
            conflict_hospital = existing.first().hospital.hospital_name
            raise CommandError(
                f"Webhook URL {webhook_url} is already used by hospital '{conflict_hospital}'. "
                f"Each hospital must have its own unique webhook."
            )

        tpl, created = WhatsappTemplate.objects.update_or_create(
            hospital=hospital,
            template_type=tpl_type,
            defaults={
                "template_name": tpl_name,
                "webhook_url": webhook_url,
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} {tpl_type} template for hospital '{hospital.hospital_name}' "
                f"→ template={tpl_name}, webhook={webhook_url}"
            )
        )
