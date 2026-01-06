from django import forms
from .models import Service


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["service_name", "service_fees"]  # ✅ hospital REMOVED
        widgets = {
            "service_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter service name",
            }),
            "service_fees": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Enter fees",
                "min": 0,
            }),
        }
