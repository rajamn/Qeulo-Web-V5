from django.urls import path
from .views_regular import (
    prescribe_patient, prescription_pdf, view_prescriptions, prescription_entry,
    save_user_preset, get_patient_details, notes_autocomplete, drug_autocomplete,
    prescription_success, rx_templates_list, get_prescription_template,
    rx_template_items, save_rx_template, apply_rx_template,
    prescription_print_regular)

from .views_ai_wizard import (
    edit_history,
    edit_symptoms, autosave_draft, edit_findings, edit_diagnosis,
    ai_suggestions, ai_add_drug, 
    ai_finalize, ai_start, ai_review, ai_discard,ai_prescription,ai_copy_old_prescription,
    add_history_template, ai_prescription_manual,ai_prescription_print_builder
)
from .views_ajax import ajax_add_drug,drug_autocomplete


app_name = "prescription"

urlpatterns = [

    # ----------------------------
    # Regular Prescription Module
    # ----------------------------
    path('', prescription_entry, name='prescription'),
    path("write/", prescribe_patient, name='prescribe_patient'),
    path('view/', view_prescriptions, name='view_prescriptions'),
    

    # AJAX
    path('api/patient-details/', get_patient_details, name='get_patient_details'),
    path('api/autocomplete/', notes_autocomplete, name='notes_autocomplete'),
    path('drugs/api/autocomplete/', drug_autocomplete, name='drug_autocomplete'),
    path('save_user_preset/', save_user_preset, name='save_user_preset'),
    path('success/', prescription_success, name='prescription_success'),

    # Templates API
    path("api/templates/", rx_templates_list, name="rx_templates_list"),
    path("api/templates/<int:template_id>/", get_prescription_template, name="get_prescription_template"),
    path("api/templates/<int:template_id>/items/", rx_template_items, name="rx_template_items"),
    path("api/templates/apply/", apply_rx_template, name="apply_rx_template"),
    path("api/templates/save/", save_rx_template, name="save_rx_template"),

    # ----------------------------
# AI Prescription Wizard
# ----------------------------

# Entry points

path("start/", ai_start, name="ai_rx_start"),

# Steps
path("ai/<int:draft_id>/history/", edit_history, name="ai_rx_history"),
path("ai/<int:draft_id>/symptoms/", edit_symptoms, name="ai_rx_symptoms"),
path("ai/<int:draft_id>/autosave/", autosave_draft, name="ai_rx_autosave"),
path("ai/<int:draft_id>/findings/", edit_findings, name="ai_rx_findings"),
path("ai/<int:draft_id>/diagnosis/", edit_diagnosis, name="ai_rx_diagnosis"),

# AI suggestions
path("ai/<int:draft_id>/ai-suggestions/", ai_suggestions, name="ai_rx_ai_suggestions"),
path("ai/<int:draft_id>/add-drug/", ai_add_drug, name="ai_rx_add_drug"),

# Review + Finalize
path("ai/<int:draft_id>/review/", ai_review, name="ai_rx_review"),
path("ai/<int:draft_id>/finalize/", ai_finalize, name="ai_rx_finalize"),
path("ai/<int:draft_id>/discard/", ai_discard, name="ai_rx_discard"),


# Prescription building
path("ai/<int:draft_id>/prescription/",ai_prescription, name="ai_rx_prescription"),
path("print/<int:rx_id>/", prescription_print_regular, name="prescription_print"),


# Copy old prescription (optional if using past Rx)
path("ai/<int:draft_id>/copy/<int:prescription_id>/", ai_copy_old_prescription, name="ai_copy_old_prescription"),

# Custom history template
path("ai/<int:draft_id>/add_history_template/", add_history_template, name="add_history_template"),

path("ai/<int:draft_id>/prescription/manual/",ai_prescription_manual,name="ai_rx_prescription_manual"),
path("rx/print/<int:rx_id>/", ai_prescription_print_builder, name="ai_prescription_print_builder"),

path("ajax/drug-autocomplete/", drug_autocomplete, name="drug_autocomplete"),
path("ajax/add-drug/", ajax_add_drug, name="ajax_add_drug"),
]

