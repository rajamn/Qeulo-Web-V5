from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
# from django.forms import modelformset_factory
from prescription.models import PrescriptionMaster, PrescriptionDetails, AppointmentDetails
from doctors.models import Doctor


@login_required
def view_prescriptions(request):
    """
    Read-only prescription list for NON-doctor users
    (Reception, Accountant, Hospital Admin).
    """

    user = request.user

    # ---- 1. Hard block doctors ----
    if user.role and user.role.role_name == "doctor":
        return HttpResponseForbidden("Doctors should not access this page.")

    # ---- 2. Hospital is guaranteed by model ----
    hospital = user.hospital

    # ---- 3. Doctors list (for filter dropdown only) ----
    doctors = Doctor.objects.filter(hospital=hospital).order_by("doctor_name")
    selected_doctor = None

    # ---- 4. Base prescription queryset (HOSPITAL-SCOPED) ----
    prescriptions = (
        PrescriptionMaster.objects
        .filter(doctor__hospital=hospital)
        .select_related(
            "patient",
            "patient__contact",
            "doctor",
            "appointment",
            "appointment__doctor",
        )
    )

    # ---- 5. Optional doctor filter ----
    doctor_pk = request.GET.get("doctor")
    if doctor_pk:
        selected_doctor = get_object_or_404(doctors, pk=doctor_pk)
        prescriptions = prescriptions.filter(doctor=selected_doctor)

    # ---- 6. Order & limit ----
    prescriptions = prescriptions.order_by("-prescribed_on")[:20]

    return render(
        request,
        "prescription/view_prescriptions.html",
        {
            "doctors": doctors,
            "selected_doctor": selected_doctor,
            "prescriptions": prescriptions,
        }
    )

