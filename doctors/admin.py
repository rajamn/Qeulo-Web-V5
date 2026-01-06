from django.contrib import admin

# Register your models here.
from .models import Doctor

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('doctor_name', 'doc_mobile_num', 'hospital', 'fees', 'average_time_minutes', 'start_time')
    search_fields = ('doctor_name', 'doc_mobile_num')
    list_filter = ('hospital',)
