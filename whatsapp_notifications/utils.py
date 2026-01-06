# whatsapp_notifications/utils.py
from datetime import timedelta, datetime,date
from appointments.models import AppointmentDetails
from .services import send_whatsapp_template


# whatsapp_notifications/utils.py

def send_reschedule_notifications(hospital, doctor, delay_minutes):
    """
    Sends reschedule WhatsApp messages to all patients currently in queue
    for a given doctor, applying the delay in minutes and updating ETAs.
    """
    today = date.today()
    queued_appts = AppointmentDetails.objects.filter(
        hospital=hospital,
        doctor=doctor,
        appointment_on=today,
        completed=AppointmentDetails.STATUS_IN_QUEUE
    ).order_by("que_pos")

    results = []

    for appt in queued_appts:
        # 🔹 Update ETA: if available, shift by delay_minutes
        if appt.eta:
            new_eta = (
                datetime.combine(appt.appointment_on, appt.eta)
                + timedelta(minutes=delay_minutes)
            ).time()
            appt.eta = new_eta
            appt.save(update_fields=["eta"])

        # 🔹 Prepare placeholders for DoubleTick template
        placeholders = [
            appt.patient.patient_name,            # 1. Patient name
            doctor.doctor_name,                   # 2. Doctor name
            str(delay_minutes),                   # 3. Delay in minutes
            str(appt.token_num),                  # 4. Token number
            appt.eta.strftime("%H:%M") if appt.eta else "TBD",  # 5. Updated ETA
        ]

        try:
            response = send_whatsapp_template(
                hospital=hospital,
                template_name="appointment_reschedule_universal",
                placeholders=placeholders,
                recipient_number=appt.mobile_num,
                patient=appt.patient,
                doctor=doctor,
            )
            results.append({
                "patient": appt.patient.patient_name,
                "status": "sent",
                "response": response
            })
        except Exception as e:
            results.append({
                "patient": appt.patient.patient_name,
                "status": "failed",
                "error": str(e)
            })

    return results


# whatsapp_notifications/utils.py
def classify_inbound_message(text: str) -> str:
    if not text:
        return "UNKNOWN"
    t = text.strip().lower()

    accept_keywords = ["yes", "ok", "okay", "accept", "confirmed", "will come"]
    cancel_keywords = ["no", "cancel", "not coming", "can't", "cannot", "won't come"]

    if any(word in t for word in accept_keywords):
        return "ACCEPTED"
    if any(word in t for word in cancel_keywords):
        return "CANCELLED"
    return "QUERY"
