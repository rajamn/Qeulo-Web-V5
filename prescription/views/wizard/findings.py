from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from prescription.models import PrescriptionDraft, PrescriptionMaster
from patients.models import Patient
from visit_workspace.models import VisitDocument
from vitals.models import PatientVital
from doctors.utils import get_doctor_sidebar_ctx
from prescription.constants.core_findings import CORE_FINDINGS
from prescription.constants.physician_findings import PHYSICIAN_FINDINGS
from prescription.constants.pediatric_findings import PEDIATRIC_FINDINGS

# ---------------------------------------------------------
# 5. STEP-3: FINDINGS
# ---------------------------------------------------------

@login_required
def findings_step(request, draft_id):

    doctor = getattr(request.user, "doctor", None)

    if not doctor:
        return HttpResponseForbidden("Doctor access required")
    
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

    data = draft.data or {}

    # ---------------------------------------------
    # Carry-forward findings ONLY ONCE
    # ---------------------------------------------
    if "notes_findings" not in data.get("carried", {}):
        last_rx = (
            PrescriptionMaster.objects
            .filter(patient=patient, doctor=draft.doctor)
            .order_by("-id")
            .first()
        )
        if last_rx and last_rx.notes_findings:
            carried = data.get("carried", {})
            carried["notes_findings"] = last_rx.notes_findings
            data["carried"] = carried
            draft.data = data
            draft.save(update_fields=["data"])

    carried_findings = data.get("carried", {}).get("notes_findings", "")
    existing_findings = data.get("findings", "")

    # ------------------------
    # Documents & vitals
    # ------------------------
    visit_docs = VisitDocument.objects.filter(
        hospital=draft.hospital,
        patient=patient
    ).order_by("-created_at")

    latest_vitals = PatientVital.objects.filter(
        hospital=draft.hospital,
        patient=patient
    ).order_by("-recorded_at").first()

    # Build vitals block (your logic is good)
    vitals_block = build_vitals_block(latest_vitals)

    if request.method == "POST":
        free_text = request.POST.get("findings", "")

        merged = merge_findings(
            carried=carried_findings,
            free_text=free_text,
        )

        data["findings"] = merged
        draft.data = data
        draft.current_step = "findings"
        draft.save(update_fields=["data", "current_step", "updated_at"])

        # 🔑 Always return to Decision Hub
        return redirect("prescription:ai_rx_decision", draft_id=draft.id)

    context = {
        "draft": draft,
        "patient": patient,
        "findings": existing_findings,
        "visit_docs": visit_docs,
        "latest_vitals": latest_vitals,
        "vitals_block": vitals_block,
        "findings_phrases": build_findings_phrases(doctor),
        "is_edit_mode": True,
        "dw_mode": "edit",
    }

    
    context["sidebar_ctx"] = get_doctor_sidebar_ctx(request.user)

    return render(request, "prescription/wizard/findings.html", context)

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



def build_findings_phrases(doctor):
    primary = doctor.primary_specialty
    secondary = doctor.secondary_specialties or []
    applicable = set([primary, *secondary, "general"])

    findings_phrases = {}
    seen = set()

    def add(sec):
        label = sec.get("label")
        phrases = sec.get("phrases") or sec.get("content", [])
        specialties = set(sec.get("specialties", []))

        if not label or not phrases:
            return
        if label in seen:
            return
        if specialties and not specialties.intersection(applicable):
            return

        findings_phrases[label] = phrases
        seen.add(label)

    # CORE
    for sec in normalize_sections(CORE_FINDINGS):
        add(sec)

    # PHYSICIAN
    if "physician" in applicable:
        for sec in normalize_sections(PHYSICIAN_FINDINGS):
            add(sec)

    # PEDIATRIC
    if "pediatrician" in applicable:
        for sec in normalize_sections(PEDIATRIC_FINDINGS):
            add(sec)

    return findings_phrases




def build_vitals_block(latest_vitals):
    # ------------------------
    # Build vitals block
    # ------------------------
    if latest_vitals:
        bmi = latest_vitals.bmi if latest_vitals.bmi not in [None, "", 0] else "—"

        vitals_block = (
            "Vitals:\n"
            f"Ht {latest_vitals.height_cm or '—'} cm · "
            f"Wt {latest_vitals.weight_kg or '—'} kg (BMI {bmi}) · "
            f"Temp {latest_vitals.temperature_c or '—'} °C\n"
            f"BP {latest_vitals.bp_systolic or '—'}/{latest_vitals.bp_diastolic or '—'} · "
            f"Pulse {latest_vitals.pulse_bpm or '—'} bpm · "
            f"SpO₂ {latest_vitals.spo2_percent or '—'}%"
        )
    else:
        vitals_block = (
            "Vitals:\n"
            "Ht:    · Wt:    · Temp:   \n"
            "BP:    · Pulse:    · SpO₂:   "
        )


def merge_findings(carried="", free_text=""):
    parts = []

    if carried:
        parts.extend([line.strip() for line in carried.splitlines() if line.strip()])

    if free_text:
        parts.extend([line.strip() for line in free_text.splitlines() if line.strip()])

    seen = set()
    final = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            final.append(p)

    return "\n".join(final)
