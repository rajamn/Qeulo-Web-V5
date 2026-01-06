from django.contrib import admin
from .models import WhatsappConfig, WhatsappMessageLog

@admin.register(WhatsappConfig)
class WhatsappConfigAdmin(admin.ModelAdmin):
    list_display = ("hospital", "active", "send_on_registration", "send_reminders", "send_followups", "send_reschedules", "updated_at")
    list_filter = ("active", "send_on_registration", "send_reminders", "send_followups", "send_reschedules")
    search_fields = ("hospital__name",)
    readonly_fields = ("updated_at",)   # ✅ make sure only fields that exist are readonly

@admin.register(WhatsappMessageLog)
class WhatsappMessageLogAdmin(admin.ModelAdmin):
    list_display = ("hospital", "patient", "doctor", "template_name", "recipient_number", "status", "created_at")
    list_filter = ("status", "template_name", "hospital")
    search_fields = ("recipient_number", "patient__patient_name", "doctor__doctor_name")
    readonly_fields = ("created_at", "updated_at")
