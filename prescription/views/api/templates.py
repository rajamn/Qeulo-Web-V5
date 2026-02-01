from django.contrib.auth.decorators import login_required, user_passes_test
from django.http  import JsonResponse
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from drugs.models import Drug, DrugTemplate, DrugTemplateItem
from doctors.models import Doctor
from django.db import transaction
import json

@login_required
def rx_templates_list(request):
  """Return the current doctor's templates for the select dropdown."""
  doctor = getattr(request.user, "doctor_profile", None) or getattr(request.user, "doctor", None)
  if not doctor or not isinstance(doctor, Doctor):
      return JsonResponse({"ok": False, "templates": []})

  qs = DrugTemplate.objects.filter(doctor=doctor).order_by('-created_at')
  data = [{"id": t.id, "name": t.name, "created_at": t.created_at.isoformat()} for t in qs]
  return JsonResponse({"ok": True, "templates": data})


@login_required
def rx_template_items(request, pk: int):
  """Return items for a given template (doctor-scoped)."""
  doctor = getattr(request.user, "doctor_profile", None) or getattr(request.user, "doctor", None)
  if not doctor or not isinstance(doctor, Doctor):
      return JsonResponse({"ok": False, "error": "Unauthorized"}, status=403)

  try:
      t = DrugTemplate.objects.get(pk=pk, doctor=doctor)
  except DrugTemplate.DoesNotExist:
      return JsonResponse({"ok": False, "error": "Template not found"}, status=404)

  items = [{
      "drug_name": it.drug_name,
      "composition": it.composition,
      "dosage": it.dosage,
      "frequency": it.frequency,
      "duration": it.duration,
      "food_order": it.food_order,
  } for it in t.items.all().order_by('id')]

  return JsonResponse({"ok": True, "items": items, "name": t.name})


@login_required
def get_prescription_template(request, template_id: int):
    """
    Returns template items:
    [
      {"drug_name":"...", "composition":"...", "dosage":"...", "frequency":"...", "duration":"...", "food_order":"..."},
      ...
    ]
    """
    user = request.user
    doctor = getattr(user, "doctor_profile", None) or getattr(user, "doctor", None)
    hospital = getattr(user, "hospital", None) or getattr(getattr(doctor, "hospital", None), "pk", None)

    try:
        t = DrugTemplate.objects.select_related("doctor", "hospital").get(pk=template_id)
    except DrugTemplate.DoesNotExist:
        raise Http404("Template not found")

    # Visibility rules identical to list endpoint
    allowed = False
    if t.doctor_id and doctor and t.doctor_id == getattr(doctor, "id", None):
        allowed = True
    elif t.doctor_id is None and t.hospital_id and hospital and t.hospital_id == hospital:
        allowed = True
    elif t.doctor_id is None and t.hospital_id is None:
        allowed = True

    if not allowed:
        return JsonResponse({"ok": False, "error": "Not allowed"}, status=403)

    items = list(
        DrugTemplateItem.objects
        .filter(template=t)
        .order_by("id")
        .values(
            "drug_name", "composition", "dosage", "frequency", "duration", "food_order"
        )
    )
    return JsonResponse({"ok": True, "id": t.id, "name": t.name, "items": items})

@login_required
@require_POST
def apply_rx_template(request):
    try:
        payload = json.loads(request.body or "{}")
        template_id = int(payload.get("template_id") or 0)
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    if not template_id:
        return JsonResponse({"ok": False, "error": "Template id is required"}, status=400)

    doctor = getattr(request.user, "doctor_profile", None) or getattr(request.user, "doctor", None)
    if not doctor:
        return JsonResponse({"ok": False, "error": "Unauthorized"}, status=403)

    try:
        tmpl = DrugTemplate.objects.get(id=template_id, doctor=doctor)
    except DrugTemplate.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Template not found"}, status=404)

    items = [{
        "drug_name": it.drug_name,
        "composition": it.composition,
        "dosage": it.dosage,
        "frequency": it.frequency,
        "duration": it.duration,
        "food_order": it.food_order,
    } for it in tmpl.items.all().order_by('id')]

    return JsonResponse({"ok": True, "name": tmpl.name, "items": items})


@login_required
@require_POST
def save_rx_template(request):
    """
    Payload JSON:
    {
      "name": "Viral Fever - Adults",
      "details": [
        {"drug_name":"Paracetamol", "composition":"...", "dosage":"500 mg", "frequency":"TID", "duration":"5 days", "food_order":"AF"},
        ...
      ]
    }
    """
    try:
        payload = json.loads(request.body or "{}")
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    name = (payload.get("name") or "").strip()
    details = payload.get("details") or []
    if not name:
        return JsonResponse({"ok": False, "error": "Template name is required"}, status=400)
    if not isinstance(details, list) or not details:
        return JsonResponse({"ok": False, "error": "No items to save"}, status=400)

    # Doctor & hospital context
    doctor = getattr(request.user, "doctor_profile", None) or getattr(request.user, "doctor", None)
    if not doctor or not isinstance(doctor, Doctor):
        return JsonResponse({"ok": False, "error": "Only doctors can save templates"}, status=403)
    hospital = getattr(request.user, "hospital", None) or getattr(doctor, "hospital", None)

    def match_drug(drug_name: str):
        """
        Best-effort match honoring your scoping rules:
        1) doctor-specific
        2) hospital-level (Doctor null)
        3) global (no hospital/doctor)
        """
        qs = Drug.objects.filter(drug_name__iexact=drug_name.strip())
        if doctor:
            m = qs.filter(added_by_doctor=doctor).first()
            if m: return m
        if hospital:
            m = qs.filter(hospital=hospital, added_by_doctor__isnull=True).first()
            if m: return m
        return qs.filter(hospital__isnull=True, added_by_doctor__isnull=True).first()

    with transaction.atomic():
        tmpl = DrugTemplate.objects.create(doctor=doctor, name=name)

        items = []
        matched_ids = set()

        for idx, row in enumerate(details):
            dn = (row.get("drug_name") or "").strip()
            if not dn:
                continue
            comp = (row.get("composition") or "").strip()
            dos  = (row.get("dosage") or "").strip()
            freq = (row.get("frequency") or "").strip()
            dur  = (row.get("duration") or "").strip()
            food = (row.get("food_order") or "").strip()

            matched = match_drug(dn)
            if matched:
                matched_ids.add(matched.id)

            items.append(DrugTemplateItem(
                template=tmpl,
                drug=matched,
                drug_name=dn,
                composition=comp,
                dosage=dos,
                frequency=freq,
                duration=dur,
                food_order=food,
            ))

        if not items:
            return JsonResponse({"ok": False, "error": "No valid rows"}, status=400)

        DrugTemplateItem.objects.bulk_create(items)

        # Fill the M2M with any matched catalog drugs (optional but keeps your M2M meaningful)
        if matched_ids:
            tmpl.drugs.add(*matched_ids)

    return JsonResponse({"ok": True, "template_id": tmpl.id, "name": tmpl.name, "items": len(items)})
