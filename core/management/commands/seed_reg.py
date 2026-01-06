# core/management/commands/seed_patients.py

import sys
import random
from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.apps import apps
from faker import Faker


# Usage:
# python manage.py seed_patients --hospital-id=1 --doctor-ids=6,7,8 --per-doctor=4


class Command(BaseCommand):
    help = "Seed patients for specified hospital and doctors with realistic fake data (DOB instead of age)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--hospital-id',
            type=int,
            required=True,
            help="ID of the hospital to seed"
        )
        parser.add_argument(
            '--doctor-ids',
            type=str,
            required=True,
            help="Comma-separated list of doctor IDs to assign patients to"
        )
        parser.add_argument(
            '--per-doctor',
            type=int,
            default=5,
            help="How many patients to seed per doctor (default 5)"
        )

    def handle(self, *args, **options):
        fake = Faker()

        # Lookup models dynamically
        Hospital            = apps.get_model('core',        'Hospital')
        Doctor              = apps.get_model('doctors',     'Doctor')
        Service              = apps.get_model('services',    'Service')
        Contact             = apps.get_model('patients',    'Contact')
        Patient             = apps.get_model('patients',    'Patient')
        PaymentMaster       = apps.get_model('billing',     'PaymentMaster')
        PaymentTransaction  = apps.get_model('billing',     'PaymentTransaction')
        AppointmentDetails  = apps.get_model('appointments','AppointmentDetails')

        # Import helper utilities
        from appointments.utils   import get_next_queue_position
        from patients.utils       import generate_token_string
        from utils.eta_calculator import calculate_eta_time

        # Parse options
        hospital_id = options['hospital_id']
        try:
            hospital = Hospital.objects.get(id=hospital_id)
        except Hospital.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"No hospital found with id={hospital_id}"))
            sys.exit(1)

        doctor_ids = [int(x) for x in options['doctor_ids'].split(',') if x.strip().isdigit()]
        doctors = Doctor.objects.filter(id__in=doctor_ids, hospital=hospital)
        if not doctors.exists():
            self.stderr.write(self.style.ERROR(f"No matching doctors in hospital {hospital_id} for IDs {doctor_ids}"))
            sys.exit(1)

        service = Service.objects.filter(hospital=hospital).first()
        if not service:
            self.stderr.write(self.style.ERROR("No service found for that hospital"))
            sys.exit(1)

        per_doc = options['per_doctor']
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Seeding {per_doc} patients each for hospital {hospital_id}, doctors {doctor_ids}…"
        ))

        today = date.today()

        for doc in doctors:
            for i in range(per_doc):
                # Generate fake patient info
                full_name = fake.name()
                mobile    = fake.msisdn()[-10:]
                gender    = random.choice(['M', 'F', 'O'])
                referred  = fake.random_element(elements=("Dr. A", "Dr. B", "Friend", ""))

                # ✅ Generate realistic DOB (1–90 years ago)
                age_years = random.randint(1, 90)
                dob = today - timedelta(days=age_years * 365 + random.randint(0, 364))

                # Contact + Patient
                contact = Contact.objects.create(
                    mobile_num=mobile,
                    contact_name=full_name,
                    hospital=hospital
                )

                patient = Patient.objects.create(
                    contact=contact,
                    patient_name=full_name,
                    dob=dob,
                    gender=gender,
                    referred_by=referred,
                    hospital=hospital
                )

                # Payment
                today_iso = timezone.now().date()
                payment = PaymentMaster.objects.create(
                    patient=patient,
                    mobile_num=mobile,
                    hospital=hospital,
                    total_amount=0,
                    paid_on=today_iso,
                    collected_by=fake.random_element(elements=("Reception1", "Reception2")),
                )

                amount = Decimal(random.choice(["300.00", "500.00", "700.00"]))
                txn = PaymentTransaction.objects.create(
                    patient=patient,
                    payment=payment,
                    doctor=doc,
                    service=service,
                    amount=amount,
                    pay_type=fake.random_element(elements=("Cash", "Card", "UPI")),
                    paid_on=today_iso,
                    hospital=hospital
                )

                payment.total_amount = amount
                payment.save(update_fields=["total_amount"])

                # Appointment
                appt_date = timezone.now().date()
                pos_data = get_next_queue_position(doc, appt_date, hospital)
                que_pos = pos_data["next_pos"]
                completed_count = pos_data["completed_count"]

                que_pos_for_eta = int(que_pos) - int(completed_count)
                eta = calculate_eta_time(
                    doc.start_time.replace(second=0, microsecond=0),
                    doc.average_time_minutes,
                    que_pos_for_eta
                )
                token = generate_token_string()

                AppointmentDetails.objects.create(
                    patient=patient,
                    doctor=doc,
                    mobile_num=mobile,
                    hospital=hospital,
                    payment=payment,
                    appointment_on=appt_date,
                    token_num=token,
                    que_pos=que_pos,
                    eta=eta,
                    completed=-1,  # registered
                )

                self.stdout.write(self.style.SUCCESS(
                    f"• {full_name[:20]:<20} | Doc#{doc.id} | Token {token} | DOB {dob.strftime('%d-%m-%Y')}"
                ))

        self.stdout.write(self.style.SUCCESS("🎉 Done seeding patients with DOB."))
