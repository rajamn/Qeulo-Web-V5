from django import forms
from .models import PatientVital

class PatientVitalForm(forms.ModelForm):
    # Display-only field (not saved from the form; model computes BMI on save)
    bmi = forms.DecimalField(
        label="BMI",
        required=False,
        max_digits=5,
        decimal_places=2,
        disabled=True,
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = PatientVital
        # ⬇️ REMOVE 'bmi' from model fields
        fields = [
            "height_cm", "weight_kg",
            "temperature_c", "bp_systolic", "bp_diastolic",
            "spo2_percent", "pulse_bpm", "notes",
        ]
        widgets = {
            "height_cm":    forms.NumberInput(attrs={"step": "0.01", "min": "30", "class": "form-control", "placeholder": "Height (cm)"}),
            "weight_kg":    forms.NumberInput(attrs={"step": "0.01", "min": "1",  "class": "form-control", "placeholder": "Weight (kg)"}),
            "temperature_c":forms.NumberInput(attrs={"step": "0.1", "min": "30", "max": "45", "class": "form-control", "placeholder": "Temperature (°C)"}),
            "bp_systolic":  forms.NumberInput(attrs={"min": "50", "max": "260", "class": "form-control", "placeholder": "Systolic"}),
            "bp_diastolic": forms.NumberInput(attrs={"min": "30", "max": "180", "class": "form-control", "placeholder": "Diastolic"}),
            "spo2_percent": forms.NumberInput(attrs={"min": "50", "max": "100", "class": "form-control", "placeholder": "SpO₂ %"}),
            "pulse_bpm":    forms.NumberInput(attrs={"min": "20", "max": "220", "class": "form-control", "placeholder": "Pulse (bpm)"}),
            "notes":        forms.TextInput(attrs={"class": "form-control", "placeholder": "Notes (optional)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill BMI when editing an existing instance
        if self.instance and self.instance.pk:
            self.fields["bmi"].initial = self.instance.bmi

    def clean(self):
        """
        Recompute BMI for preview if the user enters height/weight
        and the form has other errors; model will compute the final value on save.
        """
        cleaned = super().clean()
        h = cleaned.get("height_cm")
        w = cleaned.get("weight_kg")
        try:
            if h and w:
                h_m = float(h) / 100.0
                if h_m > 0:
                    self.cleaned_data["bmi"] = round(float(w) / (h_m * h_m), 2)
        except Exception:
            pass
        return cleaned
