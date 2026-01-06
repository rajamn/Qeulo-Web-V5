# queue/forms.py
from django import forms
from doctors.models import Doctor

STATUS_CHOICES = [
    ("", "All Statuses"),
    ("-1", "Registered"),
    ("0",  "In Queue"),
    ("1",  "Completed"),
    ("2",  "Cancelled"),
]

class AppointmentFilterForm(forms.Form):
    doctor = forms.ModelChoiceField(
        queryset=Doctor.objects.none(),
        required=False,
        empty_label="All Doctors",
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm',
            'id':    'doctorFilter',
        })
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm',
            'id':    'statusFilter',
        })
    )
    patient = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class':       'form-control form-control-sm',
            'id':          'patientSearch',
            'placeholder': 'Type patient name',
        })
    )


    def __init__(self, *args, hospital=None, **kwargs):
        super().__init__(*args, **kwargs)
        if hospital is not None:
            self.fields['doctor'].queryset = Doctor.objects.filter(hospital=hospital)
        else:
            self.fields['doctor'].queryset = Doctor.objects.all()
