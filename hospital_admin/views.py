from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from core.decorators import hospital_admin_required
from doctors.models import Doctor
from core.models import Hospital
from .forms import DoctorEditForm
from django.contrib.auth.decorators import login_required
from core.decorators import role_required
from services.forms import ServiceForm
from services.models import Service

# --- Existing ---
@hospital_admin_required
def doctor_list(request):
    hospital = request.user.hospital
    doctors = Doctor.all_objects.filter(hospital=hospital)
    return render(request, "hospital_admin/doctor_list.html", {"doctors": doctors})

@hospital_admin_required
def doctor_edit(request, doctor_id):
    hospital = request.user.hospital
    doctor = get_object_or_404(Doctor.all_objects, pk=doctor_id, hospital=hospital)
    if request.method == "POST":
        form = DoctorEditForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, "Doctor updated successfully.")
            return redirect("hospital_admin:doctor_list")
    else:
        form = DoctorEditForm(instance=doctor)
    return render(request, "hospital_admin/doctor_edit.html", {"form": form, "doctor": doctor})


# --- NEW: Manage Services ---
@hospital_admin_required
def service_list(request):
    hospital = request.user.hospital
    services = Service.objects.filter(hospital=hospital)
    return render(request, "hospital_admin/service_list.html", {"services": services})

@hospital_admin_required
def service_edit(request, service_id=None):
    if service_id:
        service = get_object_or_404(Service, pk=service_id)
    else:
        service = None

    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.hospital = request.user.hospital  # 🔒 enforce hospital
            obj.save()
    else:
        form = ServiceForm(instance=service)

    return render(
        request,
        "hospital_admin/service_edit.html",
        {
            "form": form,
            "service": service,
        }
    )


# --- NEW: Hospital Settings ---
@hospital_admin_required
def hospital_settings(request):
    hospital = request.user.hospital
    return render(request, "hospital_admin/hospital_settings.html", {"hospital": hospital})

# Create your views here.
# hospital_admin/views/services.py

@login_required
@role_required("hospital_admin")
def service_list(request):
    """List all services for the current hospital."""
    hospital = request.user.hospital
    services = Service.objects.filter(hospital=hospital).order_by("service_name")
    return render(request, "hospital_admin/services_list.html", {
        "services": services,
    })


@login_required
@role_required("hospital_admin")
def service_upsert(request, pk=None):
    """
    Add or Edit a Service.
    If pk is None → Add mode.
    If pk exists → Edit mode.
    """
    hospital = request.user.hospital
    service = None
    is_edit = pk is not None

    if is_edit:
        service = get_object_or_404(Service, pk=pk, hospital=hospital)

    if request.method == "POST":
        name = request.POST.get("service_name", "").strip()
        fees = request.POST.get("service_fees", "").strip()

        if not name or not fees:
            messages.error(request, "Both Service Name and Fees are required.")
        else:
            fees = int(fees)
            if is_edit:
                service.service_name = name
                service.service_fees = fees
                service.save()
                messages.success(request, f"✅ Service '{name}' updated successfully.")
            else:
                Service.objects.create(
                    service_name=name,
                    service_fees=fees,
                    hospital=hospital,
                )
                messages.success(request, f"✅ Service '{name}' added successfully.")
            return redirect("hospital_admin:service_list")

    return render(request, "hospital_admin/service_upsert.html", {
        "service": service,
        "is_edit": is_edit,
    })
