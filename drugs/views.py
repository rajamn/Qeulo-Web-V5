from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q,Exists, OuterRef,Case, When, Value, CharField
from drugs.models import Drug, UserPreset, DrugTemplate, DoctorDrug
from django.forms import modelformset_factory
from prescription.forms import PrescriptionDetailForm

from prescription.models import PrescriptionDetails,PrescriptionMaster
import json
from drugs.constants import PRESETS
from django.shortcuts import render
from django.http import JsonResponse
from core.decorators import doctor_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import DrugAddForm,DrugTemplateForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_http_methods
from django.db import transaction
from drugs.forms import DrugTemplateForm
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import IntegerField


@require_GET
@login_required
def drug_autocomplete(request):
    term = (request.GET.get('term') or request.GET.get('q') or '').strip()
    if not term:
        return JsonResponse([], safe=False)

    user     = request.user
    # support either attribute name
    doctor   = getattr(user, 'doctor', None) or getattr(user, 'doctor_profile', None)
    hospital = getattr(user, 'hospital', None)

    qs = (
        Drug.objects
        .filter(drug_name__icontains=term)
        .annotate(
            priority=Case(
                When(added_by_doctor=doctor, then=Value(0)),   # doctor-specific first
                When(hospital=hospital, then=Value(1)),         # hospital next
                default=Value(2),                               # global last
                output_field=IntegerField(),
            )
        )
        .order_by('priority', 'drug_name')[:60]
    )

    # De-dupe by normalized name across scopes
    out, seen = [], set()
    for d in qs:
        key = (d.drug_name or '').strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "id": d.id,
            "label": d.drug_name,     # jQuery UI needs label/value
            "value": d.drug_name,
            "composition": d.composition or "",
            "dosage": d.dosage or "",
            "frequency": d.frequency or "",
            "duration": d.duration or "",
            "scope": (
                "doctor" if d.added_by_doctor_id == getattr(doctor, 'id', None)
                else ("hospital" if d.hospital_id == getattr(hospital, 'id', None) else "global")
            ),
        })

    return JsonResponse(out, safe=False)


# ✅ Drug autocomplete (used by drug name field)
@require_GET
@login_required
def notes_autocomplete(request):
    field = request.GET.get('field')
    term = request.GET.get('term', '').strip().lower()

    if not field or field not in PRESETS:
        return JsonResponse([], safe=False)

    presets_default = PRESETS[field]

    # 1. User-defined presets
    user_presets = list(UserPreset.objects.filter(
        user=request.user, field_name=field
    ).values_list("value", flat=True))

    # 2. Frequently used values (hospital-specific)
    used_values = list(PrescriptionDetails.objects.filter(
        prescription__hospital=request.user.hospital
    ).exclude(**{field: None}).values(field).annotate(
        count=Count(field)
    ).order_by('-count').values_list(field, flat=True)[:10])

    # 3. Combine without duplicates
    combined = user_presets + [v for v in presets_default if v not in user_presets] + \
               [v for v in used_values if v not in user_presets and v not in presets_default]

    filtered = [val for val in combined if term in val.lower()][:10]

    # ✅ Final payload with 'field'
    results = [{"label": val, "value": val, "field": field} for val in filtered]

    return JsonResponse(results, safe=False)


# ✅ Save a user-defined preset
@csrf_exempt
@login_required
def save_user_preset(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            field = data.get("field_name")
            value = data.get("value", "").strip()

            if field in PRESETS and value:
                UserPreset.objects.get_or_create(
                    user=request.user, field_name=field, value=value
                )
                return JsonResponse({"message": "Preset saved!"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


def get_combined_presets(user, field):
    user_presets = list(UserPreset.objects.filter(user=user, field_name=field).values_list("value", flat=True))
    default_presets = PRESETS.get(field, [])
    return user_presets + [v for v in default_presets if v not in user_presets]



@doctor_required
@login_required
def drug_templates(request):
    doctor = getattr(request.user, 'doctor', None)
    if not doctor:
        templates = DrugTemplate.objects.none()
    else:
        templates = DrugTemplate.objects.filter(doctor=doctor).prefetch_related('drugs').order_by('name')

    return render(request, 'drugs/templates.html', {
        'templates': templates,
    })



@doctor_required
@login_required
def drug_library(request):
    doctor = getattr(request.user, 'doctor', None)
    query = request.GET.get('q', '').strip()

    show_global = request.GET.get('show_global') == '1'
    show_hospital = request.GET.get('show_hospital')
    show_doctor = request.GET.get('show_doctor')

    # Defaults if toggles are missing
    if show_hospital is None:
        show_hospital = True
    else:
        show_hospital = show_hospital == '1'

    if show_doctor is None:
        show_doctor = True
    else:
        show_doctor = show_doctor == '1'

    if not doctor:
        drugs_qs = Drug.objects.none()
    else:
        filters = Q()
        if show_global:
            filters |= Q(hospital__isnull=True, added_by_doctor__isnull=True)
        if show_hospital:
            filters |= Q(hospital=doctor.hospital, added_by_doctor__isnull=True)
        if show_doctor:
            filters |= Q(added_by_doctor=doctor)

        drugs_qs = Drug.objects.filter(filters)

        if query:
            drugs_qs = drugs_qs.filter(drug_name__icontains=query)

        drugs_qs = drugs_qs.annotate(
            added_by=Case(
                When(added_by_doctor=doctor, then=Value('Doctor')),
                When(hospital=doctor.hospital, added_by_doctor__isnull=True, then=Value('Hospital')),
                When(hospital__isnull=True, added_by_doctor__isnull=True, then=Value('Global')),
                default=Value('Unknown'),
                output_field=CharField(),
            )
        ).order_by('drug_name')

    # Pagination: 50 drugs per page
    paginator = Paginator(drugs_qs, 50)
    page = request.GET.get('page')

    try:
        drugs = paginator.page(page)
    except PageNotAnInteger:
        drugs = paginator.page(1)
    except EmptyPage:
        drugs = paginator.page(paginator.num_pages)

    context = {
        'drugs': drugs,
        'query': query,
        'show_global': show_global,
        'show_hospital': show_hospital,
        'show_doctor': show_doctor,
    }
    return render(request, 'drugs/library.html', context)



@doctor_required
@login_required
@require_http_methods(["GET", "POST"])
def drug_library_edit(request):
    doctor = getattr(request.user, 'doctor', None)
    if not doctor:
        messages.error(request, "No doctor profile found.")
        return redirect('drug_library')

    if request.method == 'POST':
        selected_drug_ids = request.POST.getlist('selected_drugs')
        selected_drug_ids = list(map(int, selected_drug_ids)) if selected_drug_ids else []

        DoctorDrug.objects.filter(doctor=doctor).exclude(drug_id__in=selected_drug_ids).delete()

        existing_ids = set(DoctorDrug.objects.filter(doctor=doctor).values_list('drug_id', flat=True))
        new_ids = set(selected_drug_ids) - existing_ids
        new_links = [DoctorDrug(doctor=doctor, drug_id=drug_id) for drug_id in new_ids]
        DoctorDrug.objects.bulk_create(new_links)

        messages.success(request, "Your drug selections have been updated.")
        return redirect('drug_library')

    query = request.GET.get('q', '').strip()
    show_global = request.GET.get('show_global') == '1'
    show_hospital = request.GET.get('show_hospital')
    show_doctor = request.GET.get('show_doctor')

    show_hospital = True if show_hospital is None else show_hospital == '1'
    show_doctor = True if show_doctor is None else show_doctor == '1'

    filters = Q()
    if show_global:
        filters |= Q(hospital__isnull=True, added_by_doctor__isnull=True)
    if show_hospital:
        filters |= Q(hospital=doctor.hospital, added_by_doctor__isnull=True)
    if show_doctor:
        filters |= Q(added_by_doctor=doctor)

    drugs_qs = Drug.objects.filter(filters)
    if query:
        drugs_qs = drugs_qs.filter(drug_name__icontains=query)

    selected_qs = DoctorDrug.objects.filter(doctor=doctor, drug=OuterRef('pk'))

    drugs_qs = drugs_qs.annotate(
        is_selected=Exists(selected_qs),
        added_by=Case(
            When(added_by_doctor=doctor, then=Value('Doctor')),
            When(hospital=doctor.hospital, added_by_doctor__isnull=True, then=Value('Hospital')),
            When(hospital__isnull=True, added_by_doctor__isnull=True, then=Value('Global')),
            default=Value('Unknown'),
            output_field=CharField(),
        )
    ).order_by('drug_name')

    # Pagination
    paginator = Paginator(drugs_qs, 50)  # 50 per page
    page = request.GET.get('page')
    try:
        drugs = paginator.page(page)
    except PageNotAnInteger:
        drugs = paginator.page(1)
    except EmptyPage:
        drugs = paginator.page(paginator.num_pages)

    context = {
        'drugs': drugs,
        'query': query,
        'show_global': show_global,
        'show_hospital': show_hospital,
        'show_doctor': show_doctor,
    }
    return render(request, 'drugs/library_edit.html', context)



@doctor_required
@login_required
def lib_add_drug(request):
    doctor = getattr(request.user, 'doctor', None)
    next_url = request.GET.get('next') or 'drug_library_edit'

    if request.method == 'POST':
        form = DrugAddForm(request.POST, doctor=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, "Drug saved successfully.")
            return redirect(next_url)
    else:
        form = DrugAddForm(doctor=doctor)

    return render(request, 'drugs/lib_add_drug.html', {
        'form': form,
        'next': next_url,
    })



@login_required
@doctor_required
def get_template_drugs(request, template_id):
    try:
        template = DrugTemplate.objects.get(id=template_id, doctor=request.user.doctor)
    except DrugTemplate.DoesNotExist:
        return JsonResponse({'error': 'Template not found'}, status=404)

    drugs = list(template.drugs.values('id', 'drug_name', 'composition', 'dosage', 'frequency', 'duration', 'food_order'))
    return JsonResponse({'drugs': drugs})


@doctor_required
@login_required
def drug_templates(request):
    doctor = getattr(request.user, 'doctor', None)
    if not doctor:
        templates = DrugTemplate.objects.none()
    else:
        templates = DrugTemplate.objects.filter(doctor=doctor).prefetch_related('drugs').order_by('name')
    return render(request, 'drugs/templates.html', {
        'templates': templates,
    })


@doctor_required
@login_required
def add_drug_template(request):
    doctor = getattr(request.user, 'doctor', None)

    # Create a formset class for PrescriptionDetails (for adding drugs to template)
    PrescriptionDetailFormSet = modelformset_factory(
        PrescriptionDetails,
        form=PrescriptionDetailForm,
        extra=1,
        can_delete=True,
    )

    if request.method == 'POST':
        template_form = DrugTemplateForm(request.POST)
        formset = PrescriptionDetailFormSet(request.POST, queryset=PrescriptionDetails.objects.none())

        if template_form.is_valid() and formset.is_valid():
            # Save the new DrugTemplate instance
            template = template_form.save(commit=False)
            template.doctor = doctor
            template.save()

            # Save the formset's PrescriptionDetails with the template link
            details = formset.save(commit=False)
            for detail in details:
                detail.prescription_template = template
                detail.save()

            # Delete forms marked for deletion
            for deleted in formset.deleted_objects:
                deleted.delete()

            messages.success(request, "Drug template saved successfully!")
            return redirect('drug_templates')
    else:
        template_form = DrugTemplateForm()
        formset = PrescriptionDetailFormSet(queryset=PrescriptionDetails.objects.none())

    context = {
        'template_form': template_form,
        'formset': formset,
    }
    return render(request, 'drugs/add_template.html', context)


@doctor_required
@login_required
def view_drug_template(request, template_id):
    doctor = getattr(request.user, 'doctor', None)

    # Fetch the template owned by this doctor or 404
    template = get_object_or_404(DrugTemplate, id=template_id, doctor=doctor)

    return render(request, 'drugs/view_template.html', {
        'template': template,
    })


@require_POST
@doctor_required
@login_required
def delete_drug_template(request, template_id):
    doctor = getattr(request.user, 'doctor', None)
    template = get_object_or_404(DrugTemplate, id=template_id, doctor=doctor)
    template.delete()
    messages.success(request, f"Template '{template.name}' deleted successfully.")
    return redirect('drug_templates')

