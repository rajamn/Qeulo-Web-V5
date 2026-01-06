import sys
from django.core.management.base import BaseCommand
from core.management.commands._base_seed import BaseSeedCommand
from core.models import Hospital
from billing.models import Service
# usage python manage.py seed_services --all
# python manage.py seed_services --hospital-ids=1,2,5


class Command(BaseSeedCommand):
    help = "Seed default services for one or more hospitals"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--all',
            action='store_true',
            help="Apply services to all hospitals"
        )
        group.add_argument(
            '--hospital-ids',
            type=str,
            help="Comma-separated hospital IDs, e.g. --hospital-ids=1,3,7"
        )

    def seed(self):
        default_services = [
            {"service_name": "Consultation", "service_fees": 300},
            {"service_name": "Injection",   "service_fees": 100},
            {"service_name": "Dressing",    "service_fees": 300},
            {"service_name": "GRBS",        "service_fees": 100},
            {"service_name": "BP Charges",  "service_fees": 50},
            {"service_name": "Lab Charges", "service_fees": 500},
            {"service_name": "Vaccination", "service_fees": 300},
            {"service_name": "POP CAST",    "service_fees": 4000},
            {"service_name": "Procedure",   "service_fees": 500},
            {"service_name": "IV Fluids",   "service_fees": 500},
            {"service_name": "ECG",   "service_fees": 500},
            {"service_name": "Bed Charges",   "service_fees": 1500},
        ]

        # Determine our hospital queryset
        if self.options['all']:
            hospitals = Hospital.objects.all()
        else:
            ids = [int(pk) for pk in self.options['hospital_ids'].split(',')]
            hospitals = Hospital.objects.filter(id__in=ids)

        if not hospitals.exists():
            self.stderr.write(self.style.ERROR("No hospitals found."))
            sys.exit(1)

        for hosp in hospitals:
            self.stdout.write(f"\nProcessing hospital: {hosp.hospital_name} (ID {hosp.id})")
            for svc in default_services:
                obj, created = Service.objects.get_or_create(
                    hospital=hosp,
                    service_name=svc["service_name"],
                    defaults={"service_fees": svc["service_fees"]}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f" • Created {svc['service_name']}"))
                else:
                    self.stdout.write(f" • Already exists: {svc['service_name']}")
