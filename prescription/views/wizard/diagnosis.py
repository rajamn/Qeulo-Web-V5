from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from prescription.models import PrescriptionDraft, PrescriptionMaster
from prescription.models import PrescriptionDraft
from patients.models import Patient
from doctors.utils import get_doctor_sidebar_ctx
from prescription.constants.core_diagnosis import CORE_DIAGNOSIS
from prescription.constants.pediatric_diagnosis import PEDIATRIC_DIAGNOSIS
from prescription.constants.physician_diagnosis import PHYSICIAN_DIAGNOSIS

# ---------------------------------------------------------
# 6. STEP-4: DIAGNOSIS
# ---------------------------------------------------------

@login_required
def diagnosis_step(request, draft_id):
    doctor = getattr(request.user, "doctor", None)
    if not doctor:
        return HttpResponseForbidden("Doctor access required")

    draft = get_object_or_404(
        PrescriptionDraft,
        pk=draft_id,
        finalized=False,
        doctor=doctor,
    )

    patient_id = draft.data.get("patient_id")
    if not patient_id:
        return JsonResponse({"error": "Missing patient in draft"}, status=400)

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
        hospital=draft.hospital
    )

    data = draft.data or {}

    # ---------------------------------------------
    # Carry-forward diagnosis ONLY ONCE
    # ---------------------------------------------
    if "diagnosis" not in data.get("carried", {}):
        last_rx = (
            PrescriptionMaster.objects
            .filter(patient=patient, doctor=doctor)
            .order_by("-id")
            .first()
        )
        if last_rx and last_rx.diagnosis:
            carried = data.get("carried", {})
            carried["diagnosis"] = last_rx.diagnosis
            data["carried"] = carried
            draft.data = data
            draft.save(update_fields=["data"])

    carried_diagnosis = data.get("carried", {}).get("diagnosis", "")
    existing_diagnosis = data.get("diagnosis", "")

    if request.method == "POST":
        free_text = request.POST.get("diagnosis", "")

        merged = merge_diagnosis(
            carried=carried_diagnosis,
            free_text=free_text,
        )

        data["diagnosis"] = merged
        draft.data = data
        draft.current_step = "diagnosis"
        draft.save(update_fields=["data", "current_step", "updated_at"])

        return redirect("prescription:ai_rx_decision", draft_id=draft.id)

    context = {
        "draft": draft,
        "patient": patient,
        "diagnosis": existing_diagnosis,
        "carried_diagnosis": carried_diagnosis,

        # 🔑 NEW
        "diagnosis_phrases": build_diagnosis_phrases(doctor),

        "is_edit_mode": True,
        "dw_mode": "edit",
    }

    context["sidebar_ctx"] = get_doctor_sidebar_ctx(request.user)

    return render(request, "prescription/wizard/diagnosis.html", context)


def normalize_sections(source):
    """
    Accepts:
    - list[dict]
    - dict[key -> dict]
    - dict with 'systems'
    Returns: list[dict]
    """
    if not source:
        return []

    # Case 1: already list of dicts
    if isinstance(source, list):
        return [s for s in source if isinstance(s, dict)]

    # Case 2: pediatric-style dict
    if isinstance(source, dict):
        sections = []

        # normal_exam style
        if "label" in source and ("phrases" in source or "content" in source):
            sections.append({
                "label": source.get("label"),
                "phrases": source.get("phrases") or source.get("content", []),
            })

        # systems list
        if "systems" in source:
            for s in source["systems"]:
                if isinstance(s, dict):
                    sections.append(s)

        # flat dict: key → section
        for v in source.values():
            if isinstance(v, dict) and "label" in v:
                sections.append(v)

        return sections

    return []


def build_diagnosis_phrases(doctor):
    primary = doctor.primary_specialty
    secondary = doctor.secondary_specialties or []
    applicable = set([primary, *secondary, "general"])

    diagnosis_phrases = {}
    seen = set()

    def add(sec):
        label = sec.get("label")
        phrases = sec.get("phrases", [])
        specialties = set(sec.get("specialties", []))

        if not label or not phrases:
            return
        if label in seen:
            return
        if specialties and not specialties.intersection(applicable):
            return

        diagnosis_phrases[label] = phrases
        seen.add(label)

    for sec in normalize_sections(CORE_DIAGNOSIS):
        add(sec)

    for sec in normalize_sections(PHYSICIAN_DIAGNOSIS):
        add(sec)

    for sec in normalize_sections(PEDIATRIC_DIAGNOSIS):
        add(sec)

    return diagnosis_phrases


def merge_diagnosis(carried="", free_text=""):
    parts = []

    if carried:
        parts.append(carried.strip())

    if free_text:
        parts.append(free_text.strip())

    seen = set()
    final = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            final.append(p)

    return "\n".join(final)
