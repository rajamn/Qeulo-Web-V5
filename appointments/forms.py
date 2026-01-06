from django import forms
from appointments.models import AppointmentDetails
from doctors.models import Doctor
from services.models import Service
from datetime import date
import datetime


from doctors.models import Doctor

class AppointmentForm(forms.ModelForm):
    appointment_on = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    class Meta:
        model = AppointmentDetails
        fields = ['doctor', 'appointment_on']

    def __init__(self, *args, **kwargs):
        hospital_id = kwargs.pop('hospital_id', None)
        super().__init__(*args, **kwargs)
        if hospital_id:
            self.fields['doctor'].queryset = Doctor.objects.filter(hospital_id=hospital_id)
        
           # Default to today if no value is already set
        if not self.initial.get("appointment_on"):
            self.initial["appointment_on"] = datetime.date.today()
