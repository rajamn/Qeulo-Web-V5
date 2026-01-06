from django.contrib import admin
from .models import Contact, Patient


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('contact_name', 'mobile_num', 'hospital', 'created_at')
    search_fields = ('contact_name', 'mobile_num')
    list_filter = ('hospital', 'created_at')


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'contact', 'gender', 'dob', 'display_age', 'hospital', 'created_at')
    search_fields = ('patient_name', 'contact__mobile_num', 'contact__contact_name')
    list_filter = ('gender', 'hospital')

    def display_age(self, obj):
        """Show computed age based on DOB."""
        return obj.age_display()
    display_age.short_description = "Age"
