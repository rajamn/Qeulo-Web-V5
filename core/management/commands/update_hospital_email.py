from django.core.management.base import BaseCommand, CommandError
from core.models import Hospital


"""
python manage.py update_hospital_email \
  --hospital-id 3 \
  --email admin@newhospital.com

python manage.py update_hospital_email \
  --phone 9876543210 \
  --email billing@hospital.com

"""

class Command(BaseCommand):
    help = "Update hospital email address"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hospital-id",
            type=int,
            help="Hospital ID",
        )
        parser.add_argument(
            "--phone",
            type=str,
            help="Hospital phone number",
        )
        parser.add_argument(
            "--slug",
            type=str,
            help="Hospital slug",
        )
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="New hospital email address",
        )

    def handle(self, *args, **options):
        hospital_id = options.get("hospital_id")
        phone = options.get("phone")
        slug = options.get("slug")
        email = options.get("email")

        if not (hospital_id or phone or slug):
            raise CommandError(
                "You must provide one identifier: --hospital-id OR --phone OR --slug"
            )

        qs = Hospital.objects.all()

        if hospital_id:
            qs = qs.filter(id=hospital_id)
        elif phone:
            qs = qs.filter(phone_num=phone)
        elif slug:
            qs = qs.filter(slug=slug)

        hospital = qs.first()

        if not hospital:
            raise CommandError("Hospital not found")

        old_email = hospital.email
        hospital.email = email
        hospital.save(update_fields=["email"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Hospital '{hospital.hospital_name}' email updated "
                f"from '{old_email}' → '{email}'"
            )
        )
