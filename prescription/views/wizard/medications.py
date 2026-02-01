from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from prescription.models import PrescriptionDraft
from patients.models import Patient
from prescription.forms import PrescriptionMasterForm, ManualDetailFormSet
from doctors.utils import get_doctor_sidebar_ctx

@login_required
def medications_step(request, draft_id):
    draft = get_object_or_404(
        PrescriptionDraft,
        pk=draft_id,
        finalized=False,
        doctor=getattr(request.user, "doctor", None),
    )

    patient_id = draft.data.get("patient_id")
    if not patient_id:
        return JsonResponse({"error": "Missing patient in draft"}, status=400)

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
        hospital=draft.hospital
    )

    initial_data = {
        "notes_history":  draft.data.get("history", ""),
        "notes_symptoms": draft.data.get("symptoms", ""),
        "notes_findings": draft.data.get("findings", ""),
        "diagnosis":      draft.data.get("diagnosis", ""),
        "general_advice": draft.data.get("general_advice", ""),
    }

    if request.method == "POST":
        draft.data["general_advice"] = (
            request.POST.get("general_advice") or ""
        ).strip()

        total = int(request.POST.get("details-TOTAL_FORMS", 0))
        meds = []

        for i in range(total):
            prefix = f"details-{i}"

            if request.POST.get(f"{prefix}-DELETE"):
                continue

            name = (request.POST.get(f"{prefix}-drug_name") or "").strip()
            if not name:
                continue

            meds.append({
                "drug_name":  name,
                "composition": (request.POST.get(f"{prefix}-composition") or "").strip(),
                "dosage":      (request.POST.get(f"{prefix}-dosage") or "").strip(),
                "frequency":   (request.POST.get(f"{prefix}-frequency") or "").strip(),
                "duration":    (request.POST.get(f"{prefix}-duration") or "").strip(),
                "food_order":  (request.POST.get(f"{prefix}-food_order") or "").strip(),
                "instructions": (request.POST.get(f"{prefix}-instructions") or "").strip(),

            })

        if not meds:
            form = PrescriptionMasterForm(initial=initial_data, user=request.user)
            formset = ManualDetailFormSet(
                initial=[{}],
                prefix="details",
                form_kwargs={"user": request.user},
            )

            return render(
                request,
                "prescription/wizard/medications.html",
                {
                    "draft": draft,
                    "patient": patient,
                    "form": form,
                    "formset": formset,
                    "error": "Please add at least one medicine.",
                    "is_edit_mode": True,
                },
            )

        draft.data["drugs"] = meds
        draft.current_step = "medications"
        draft.save(update_fields=["data", "current_step", "updated_at"])

        return redirect("prescription:ai_rx_review", draft_id=draft.id)

    saved_rows = draft.data.get("drugs") or [{}]

    form = PrescriptionMasterForm(initial=initial_data, user=request.user)
    formset = ManualDetailFormSet(
        initial=saved_rows,
        prefix="details",
        form_kwargs={"user": request.user},
    )

    return render(
        request,
        "prescription/wizard/medications.html",
        {
            "draft": draft,
            "patient": patient,
            "form": form,
            "formset": formset,
            "is_edit_mode": True,
            "sidebar_ctx" : get_doctor_sidebar_ctx(request.user),
            "dw_mode": "edit",

        },
    )
