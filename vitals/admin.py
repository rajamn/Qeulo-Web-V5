from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import PatientVital

@admin.register(PatientVital)
class PatientVitalAdmin(admin.ModelAdmin):
    list_display = ("patient", "hospital", "recorded_at", "height_cm", "weight_kg", "bmi",
                    "temperature_c", "bp_systolic", "bp_diastolic", "spo2_percent", "pulse_bpm")
    list_filter = ("hospital", "recorded_at")
    search_fields = ("patient__patient_name",)
