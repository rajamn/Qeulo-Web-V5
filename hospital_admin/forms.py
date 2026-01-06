from django import forms
from doctors.models import Doctor

class DoctorEditForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = [
            'doctor_name',
            'doc_mobile_num',
            'average_time_minutes',
            'fees',
            'start_time',
            'consult_validity_days',
            'consult_validity_visits',
            'consult_message_template',
            'is_active',
        ]
        widgets = {
            'start_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
        }
