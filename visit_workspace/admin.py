from django.contrib import admin

# Register your models here.
# visit_workspace/admin.py

from django.contrib import admin
from .models import VisitDocument, VisitNote, PrescriptionTemplate, FavoriteDrug


@admin.register(VisitDocument)
class VisitDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "hospital", "patient", "doc_type", "description", "created_at")
    list_filter = ("hospital", "doc_type", "created_at")
    search_fields = ("patient__patient_name", "description")


@admin.register(VisitNote)
class VisitNoteAdmin(admin.ModelAdmin):
    list_display = ("id", "hospital", "patient", "note_type", "created_at")
    list_filter = ("hospital", "note_type", "created_at")
    search_fields = ("patient__patient_name", "text")


@admin.register(PrescriptionTemplate)
class PrescriptionTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "hospital", "doctor", "name", "is_active", "created_at")
    list_filter = ("hospital", "doctor", "is_active")
    search_fields = ("name", "doctor__doctor_name")


@admin.register(FavoriteDrug)
class FavoriteDrugAdmin(admin.ModelAdmin):
    list_display = ("id", "hospital", "doctor", "drug", "created_at")
    list_filter = ("hospital", "doctor")
    search_fields = ("doctor__doctor_name", "drug__drug_name")
