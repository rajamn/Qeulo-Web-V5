# core/management/commands/seed_doctors.py

from django.core.management.base import BaseCommand
from django.apps import apps
from datetime import datetime
from quelo_backend import settings


class Command(BaseCommand):
    help = "Seed doctors for a hospital (lookup by --hospital-phone)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--hospital-phone',
            required=True,
            help="Phone number of the hospital to attach these doctors to"
        )

    def handle(self, *args, **options):
        phone = options['hospital_phone']
        Hospital     = apps.get_model('core', 'Hospital')
        Doctor       = apps.get_model('doctors', 'Doctor')
        HospitalUser = apps.get_model('core', 'HospitalUser')
        Role         = apps.get_model('core', 'Role')

        try:
            hospital = Hospital.objects.get(phone_num=phone)
        except Hospital.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"No hospital found with phone {phone}"))
            return

        # doctor_data = [
        #     {"doctor_name": "Dr. Siva Subrahmanyam",     "doc_mobile_num": "9849179178", "average_time_minutes": 5, "fees": 300, "start_time": "11:00"},
        #     {"doctor_name": "Dr. Satya Kiran",           "doc_mobile_num": "7981102063", "average_time_minutes": 5, "fees": 300, "start_time": "11:00"},
            
        # ]
        doctor_data = [
            {"doctor_name": "PMC Nursing",     "doc_mobile_num": "8005222722", "average_time_minutes": 5, "fees": 300, "start_time": "11:00"},
        ]

        default_pw = getattr(settings, 'DEFAULT_USER_PASSWORD', 'changeme123')
        doctor_role = Role.objects.get(role_name='Doctor')

        for data in doctor_data:
            start_time = datetime.strptime(data["start_time"], "%H:%M").time()

            doctor, created = Doctor.objects.update_or_create(
                doc_mobile_num=data["doc_mobile_num"],
                hospital=hospital,
                defaults={
                    "doctor_name": data["doctor_name"],
                    "average_time_minutes": data["average_time_minutes"],
                    "fees": data["fees"],
                    "start_time": start_time,
                }
            )

            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"• {action} doctor {doctor.doctor_name}"))

            user_qs = HospitalUser.objects.filter(mobile_num=doctor.doc_mobile_num, hospital=hospital)

            if user_qs.exists():
                user = user_qs.first()
                user.set_password(default_pw)
                user.must_change_password = True  # Optional: force reset on next login
                user.save()
                self.stdout.write(self.style.NOTICE(f"  ↳ Password reset to default for existing user {doctor.doctor_name}"))
            else:
                HospitalUser.objects.create_user(
                    mobile_num=doctor.doc_mobile_num,
                    user_name=doctor.doctor_name,
                    hospital=hospital,
                    role=doctor_role,
                    doctor=doctor,  # 🔁 Optional: link doctor immediately if needed
                )
                self.stdout.write(self.style.SUCCESS(f"  ↳ Created user for {doctor.doctor_name}"))


        self.stdout.write(self.style.SUCCESS("✅ Done seeding doctors"))
