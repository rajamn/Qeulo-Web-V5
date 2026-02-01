from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from prescription.models import PrescriptionMaster,PrescriptionDetails


@login_required
def print_prescription(request, rx_id):
    """
    Print view specifically for AI-generated prescriptions.
    """
    master = get_object_or_404(
        PrescriptionMaster.objects.select_related("doctor", "patient", "hospital", "appointment"),
        pk=rx_id,
    )

    details = PrescriptionDetails.objects.filter(prescription=master)

    return render(
        request,
        "prescription/print/final_prescription.html",
        {"master": master, "details": details},
    )


@login_required
def prescription_view(request, rx_id):
    master = get_object_or_404(PrescriptionMaster, pk=rx_id)
    details = PrescriptionDetails.objects.filter(prescription=master)

    initial = {
        "doctorName": master.doctor.doctor_name,
        "patientName": master.patient.patient_name,
        "gender": master.patient.gender,
        "Age": master.patient.age_display,
        "diagnosis": master.diagnosis,
        "history": master.notes_history,
        "symptoms": master.notes_symptoms,
        "findings": master.notes_findings,
        "advice": master.general_advice,
        "meds": [
            {
                "name": d.drug_name,
                "dose": d.dosage,
                "freq": d.frequency,
                "dur": d.duration,
                "route": d.food_order,
            }
            for d in details
        ],
    }

    return render(
        request,
        "prescription/wizard/prescription_preview.html",
        {
            "master": master,
            "initial": initial,
            "hide_form": True,
        },
    )
