from django.shortcuts import render

# Create your views here.
# views/prescription_views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from datetime import date
from core.models import Hospital
from patients.models import Patient
from doctors.models import Doctor
from datetime import date
from django.contrib import messages
from django.utils import timezone
from appointments.models import AppointmentDetails
from django.shortcuts import render, redirect, get_object_or_404
from .models import PrescriptionMaster, PrescriptionItem, Drug, PrescriptionDetails, PrescriptionLog
from django.http import JsonResponse
# from appointments.ajax import get_queued_patients


def drug_autocomplete(request):
    query = request.GET.get("term", "")
    results = []

    if query:
        drugs = Drug.objects.filter(drug_name__icontains=query).order_by("drug_name")[:10]
        results = [
            {"id": drug.id, "label": drug.drug_name, "value": drug.drug_name, "composition": drug.composition}
            for drug in drugs
        ]

    return JsonResponse(results, safe=False)



@login_required
def prescription_screen(request):
    return render(request, 'prescription/prescribe.html')


@login_required
def prescription_screen(request):
    return prescribe_patient(request)



# prescription/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse

from .models import PrescriptionMaster, PrescriptionItem, Drug
from appointments.models import AppointmentDetails
from doctors.models import Doctor
from patients.models import Patient


@login_required
def prescribe_patient(request):
    hospital = request.user.hospital
    today = timezone.now().date()

    doctors = Doctor.objects.filter(hospital=hospital).order_by("doctor_name")
    drugs = Drug.objects.all().order_by("drug_name")

    # Only GET at first
    appointments = AppointmentDetails.objects.filter(
        hospital=hospital,
        appointment_on=today,
        completed__in=[0, None]
    ).select_related('patient', 'doctor')

    if request.method == 'POST':
        doctor_id = request.POST.get("doctor_id")
        appointment_id = request.POST.get("appointment_id")

        doctor = get_object_or_404(Doctor, id=doctor_id, hospital=hospital)
        appointment = get_object_or_404(AppointmentDetails, id=appointment_id, doctor=doctor, hospital=hospital)
        patient = appointment.patient

        history = request.POST.get("history")
        symptoms = request.POST.get("symptoms")
        findings = request.POST.get("findings")
        advice = request.POST.get("general_advice")

        master = PrescriptionMaster.objects.create(
            doctor=doctor,
            patient=patient,
            hospital=hospital,
            appointment=appointment,
            notes_history=history,
            notes_symptoms=symptoms,
            notes_findings=findings,
            general_advice=advice,
        )

        # Get all items
        drug_ids = request.POST.getlist("drug_id[]")
        drug_names_new = request.POST.getlist("drug_name_new[]")
        compositions = request.POST.getlist("composition[]")
        dosages = request.POST.getlist("dosage[]")
        frequencies = request.POST.getlist("frequency[]")
        durations = request.POST.getlist("duration[]")

        for i in range(len(compositions)):
            drug = None

            if drug_ids[i]:
                drug = Drug.objects.filter(id=drug_ids[i]).first()
            elif drug_names_new[i]:
                drug = Drug.objects.create(
                    drug_name=drug_names_new[i],
                    composition=compositions[i],
                    hospital=hospital  # optional if Drug has hospital field
                )

            PrescriptionItem.objects.create(
                prescription=master,
                drug=drug,
                brand_name=drug.drug_name if drug else "",  # fallback
                composition=compositions[i],
                dosage=dosages[i],
                frequency=frequencies[i],
                duration=durations[i],
            )

        # Mark appointment as completed
        appointment.completed = 1
        appointment.save()

        messages.success(request, "✅ Prescription saved successfully.")
        return redirect("prescribe_patient")

    return render(request, "prescription/prescribe.html", {
        "doctors": doctors,
        "appointments": appointments,
        "drugs": drugs,
    })




# appointments/views.py or wherever it's defined
def get_queued_patients(request):
    from django.http import JsonResponse
    from appointments.models import AppointmentDetails
    from django.utils import timezone

    try:
        hospital = request.user.hospital
        today = timezone.now().date()
        doctor_id = request.GET.get("doctor_id")

        appointments = AppointmentDetails.objects.filter(
            hospital=hospital,
            appointment_on=today,
            completed__in=[0, None],
        )
        if doctor_id:
            appointments = appointments.filter(doctor_id=doctor_id)

        appointments = appointments.select_related("patient")

        print(f"✅ Found {appointments.count()} appointments")

        data = [
            {
                "id": appt.appoint_id,
                "patient_name": appt.patient.patient_name,
                "token_num": appt.token_num
            }
            for appt in appointments
        ]
        return JsonResponse(data, safe=False)

    except Exception as e:
        print("❌ Error in get_queued_patients:", e)
        return JsonResponse({"error": str(e)}, status=500)
