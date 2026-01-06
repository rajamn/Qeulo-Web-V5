# core/management/commands/seed_doctors.py
#usage to deactivae
#python manage.py seed_doctors --hospital-phone=1234567890 --deactivate=9848031921

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
        parser.add_argument(
            '--deactivate',
            help="Doctor mobile number to deactivate (soft delete)"
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

        doctor_data = [
            {"doctor_name": "Dr. Prabhath Kiran Reddy",     "doc_mobile_num": "7013912650", "average_time_minutes": 10, "fees": 400, "start_time": "11:00"},
            {"doctor_name": "Dr. V. Krishna Prasad",        "doc_mobile_num": "9848199567", "average_time_minutes": 15, "fees": 400, "start_time": "11:00"},
            {"doctor_name": "Dr. DVS Pratap",               "doc_mobile_num": "9848031921", "average_time_minutes": 5,  "fees": 500, "start_time": "18:30"},
            {"doctor_name": "Dr. A. Kranthi Kiran",         "doc_mobile_num": "7013212911", "average_time_minutes": 10, "fees": 500, "start_time": "10:00"},
            {"doctor_name": "Dr. Harish Goutham Medipati",  "doc_mobile_num": "7981168911", "average_time_minutes": 10, "fees": 500, "start_time": "08:00"},
            {"doctor_name": "Dr. P. Sai Kumar",             "doc_mobile_num": "8897509606", "average_time_minutes": 15, "fees": 500, "start_time": "11:00"},
            {"doctor_name": "Dr. P. Annapurna",             "doc_mobile_num": "9985142454", "average_time_minutes": 10, "fees": 500, "start_time": "10:00"},
            {"doctor_name": "Dr. Y. S. R. Shanthi Navyatha", "doc_mobile_num": "9866517035", "average_time_minutes": 20, "fees": 850, "start_time": "17:00"},
            {"doctor_name": "Dr. Francis Sridhar Katumalla","doc_mobile_num": "7981856491", "average_time_minutes": 10, "fees": 500, "start_time": "17:00"},
            {"doctor_name": "Dr. Swetha","doc_mobile_num": "9849462520", "average_time_minutes": 10, "fees": 400, "start_time": "15:00"},
            {"doctor_name": "Dr. Lathaswi","doc_mobile_num": "9908319035", "average_time_minutes": 10, "fees": 600, "start_time": "09:00"},
            {"doctor_name": "Dr. Lavanya","doc_mobile_num": "9866533964", "average_time_minutes": 10, "fees": 750, "start_time": "09:00"},
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
                user.save()
                self.stdout.write(self.style.NOTICE(f"  ↳ Updated password for existing user {doctor.doctor_name}"))
            else:
                HospitalUser.objects.create_user(
                    mobile_num=doctor.doc_mobile_num,
                    user_name=doctor.doctor_name,
                    hospital=hospital,
                    role=doctor_role
                )
                self.stdout.write(self.style.SUCCESS(f"  ↳ Created user for {doctor.doctor_name}"))

        self.stdout.write(self.style.SUCCESS("✅ Done seeding doctors"))
