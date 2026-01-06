from django.core.management.base import BaseCommand
from datetime import date
from appointments.models import AppointmentDetails


class Command(BaseCommand):
    help = "Print all appointment IDs for the current date"

    def handle(self, *args, **kwargs):
        today = date.today()

        self.stdout.write(self.style.WARNING(f"\nAppointments for: {today}\n"))
        
        appointments = AppointmentDetails.objects.filter(appointment_on=today)

        if not appointments.exists():
            self.stdout.write(self.style.ERROR("No appointments found for today."))
            return

        for appt in appointments.order_by("doctor", "token_num"):
            self.stdout.write(
                self.style.SUCCESS(
                    f"Appt ID: {appt.appoint_id} | "
                    f"Patient: {appt.patient.patient_name} | "
                    f"Doctor: {appt.doctor.doctor_name} | "
                    f"Token: {appt.token_num} | "
                    f"Status: {appt.get_completed_display()}"
                )
            )

        self.stdout.write(self.style.WARNING("\nDone.\n"))
