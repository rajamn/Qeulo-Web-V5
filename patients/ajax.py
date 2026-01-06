from django.shortcuts import render
from django.http import JsonResponse
from datetime import date
from utils.eta_calculator import calculate_eta_time
from appointments.utils import get_next_queue_position
from doctors.models import Doctor
from django.utils import timezone
import logging

#patients/ajax.py

def get_eta_ajax(request):
    logger = logging.getLogger(__name__)
    doctor_id = request.GET.get("doctor_id")
    hospital = request.user.hospital

    try:
        doctor = Doctor.objects.get(pk=doctor_id, hospital=hospital)
        pos_data = get_next_queue_position(doctor, date.today(), hospital)
        queue_pos = pos_data["next_pos"]
        completed_count = pos_data["completed_count"]
        
        # calculate queue_pos for eta
        queue_pos_for_eta = queue_pos - completed_count
        eta = calculate_eta_time(doctor.start_time, doctor.average_time_minutes, queue_pos_for_eta)
        return JsonResponse({"eta": eta.strftime("%H:%M")})
    except Exception as e:
        logger.warning(f"ETA fetch failed: {e}")
        return JsonResponse({"eta": None, "error": str(e)}, status=400)

    


def get_queued_patients(request):
    doctor_id = request.GET.get("doctor_id")
    hospital = request.user.hospital  # ✅ use hospital from logged-in user
    today = timezone.now().date()

    appointments = appointments.AppointmentDetails.objects.filter(
        doctor_id=doctor_id,
        hospital=hospital,
        appointment_on=today,
        completed__in=[0, None]
    ).select_related('patient')

    data = [
        {
            'id': appt.id,
            'patient_name': appt.patient.patient_name,
            'token_num': appt.token_num,
        }
        for appt in appointments
    ]
    return JsonResponse(data, safe=False)

