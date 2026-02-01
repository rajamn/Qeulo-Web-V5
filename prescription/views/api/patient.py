from django.contrib.auth.decorators import login_required, user_passes_test
from appointments.models import AppointmentDetails
from django.http  import JsonResponse
from datetime import date


@login_required
def get_patient_details(request):
    appt_id = request.GET.get('appointment')
    data = {
        "patient_name": None,
        "age_years": None,
        "age_months": None,
        "gender": None,
        "source": None,
    }
    if appt_id:
        try:
            appt = AppointmentDetails.objects.select_related("patient").get(pk=int(appt_id))
            patient = appt.patient
            # Name
            data["patient_name"] = patient.patient_name
            # Gender (assuming a .gender field on Patient)
            data["gender"] = getattr(patient, "gender", "")
            # Source comes from appointment
            data["source"] = getattr(appt, "source", "")
            # Calculate age if DOB exists, else fallback to age fields
            dob = getattr(patient, "date_of_birth", None)
            if dob:
                today = date.today()
                years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                months = (today.month - dob.month) % 12
                data["age_years"] = years
                data["age_months"] = months
            else:
                data["age_years"] = getattr(patient, "age_years", None)
                data["age_months"] = getattr(patient, "age_months", None)
        except (AppointmentDetails.DoesNotExist, ValueError):
            pass

    return JsonResponse(data)
