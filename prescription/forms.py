from django import forms
from django.utils import timezone
from django.forms import formset_factory
from .models import PrescriptionMaster, PrescriptionDetails
from drugs.models import UserPreset,Drug
from drugs.constants import (HISTORY_PRESETS,SYMPTOM_PRESETS,FINDINGS_PRESETS,GENERAL_ADVICE_PRESETS,)
from appointments.models import AppointmentDetails
from doctors.models import Doctor
from datetime import date


# Custom choice field to display only patient name and queue position
class AppointmentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.patient.patient_name} — Pos {obj.que_pos}"

class CompletedAppointmentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.patient.patient_name} — Pos {obj.que_pos}"

class TagListField(forms.Field):
    """
    A Field that accepts a list of strings via <select multiple>
    (so TomSelect can tag/create), but skips choice-validation.
    """
    def __init__(self, *args, placeholder="", **kwargs):
        kwargs.setdefault('required', False)
        widget = forms.SelectMultiple(attrs={
            'class': 'tomselect',
            'data-placeholder': placeholder,
        })
        super().__init__(widget=widget, *args, **kwargs)

    def to_python(self, value):
        # value is already a list of strings from POST
        return value or []

    def validate(self, value):
        # skip Django's default choice validation entirely
        return


class PrescriptionMasterForm(forms.ModelForm):
     # doctor set from request.user in view
    doctor = forms.ModelChoiceField(
        queryset=Doctor.objects.none(),
        widget=forms.HiddenInput(),
        required=False,
    )
    appointment = forms.ModelChoiceField(
        queryset=AppointmentDetails.objects.none(),
        label="Queued Patients",
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'patient-queue',
        })
    )
    completed_patient = forms.ModelChoiceField(
        queryset=AppointmentDetails.objects.none(),
        label="Completed Patients",
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'patient-completed',
            'onchange': "handlePatientSelection(this.value, 'Completed')",
        })
    )

    # before: forms.CharField(...)
    notes_history = forms.MultipleChoiceField(
        required=False,
        label="History",
        choices=[],
        widget=forms.SelectMultiple(attrs={
            'class': 'tomselect notes-history-select',
            'data-placeholder': 'Select history…'
        })
    )
    notes_symptoms = forms.MultipleChoiceField(
        required=False,
        label="Symptoms",
        choices=[],
        widget=forms.SelectMultiple(attrs={
            'class': 'tomselect notes-symptoms-select',
            'data-placeholder': 'Select symptoms…'
        })
    )
    notes_findings = forms.MultipleChoiceField(
        required=False,
        label="Findings",
        choices=[],
        widget=forms.SelectMultiple(attrs={
            'class': 'tomselect notes-findings-select',
            'data-placeholder': 'Select findings…'
        })
    )
    diagnosis = forms.CharField(
        required=False,
        label="Diagnosis",
        widget=forms.Textarea(attrs={
            "rows": 2,
            "class": "form-control",
            "placeholder": "Enter diagnosis (optional)…",
        })
    )
    general_advice = forms.MultipleChoiceField(
        required=False,
        label="General Advice",
        choices=[],
        widget=forms.SelectMultiple(attrs={
            'class': 'tomselect general-advice-select',
            'data-placeholder': 'Select general advice…'
        })
    )

    
    class Meta:
        model = PrescriptionMaster
        fields = [
            "doctor",
            "appointment",
            "completed_patient",
            "diagnosis",
            "notes_history",
            "notes_symptoms",
            "notes_findings",
            "general_advice",
        ]


        
        widgets = {
    'appointment': forms.Select(attrs={
            'class': 'form-select', 'id': 'patient-queue',
            'onchange': (
                "if(this.value){"
                "  window.location.href="
                "    '{% url \"prescribe_patient\" %}?appointment=' + this.value;"
                "}"
            ),
        }),
    'completed_patient': forms.Select(attrs={
        'class': 'form-select', 'id': 'patient-completed',
        'onchange': (
            "if(this.value){"
            "  window.location.href="
            "    '{% url \"prescribe_patient\" %}?completed_patient=' + this.value;"
            "}"
        ),
        }),
    }


    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        hospital = getattr(user, 'hospital', None)

        # Doctor queryset
        self.fields['doctor'].queryset = Doctor.objects.filter(hospital=hospital)
        # Appointment querysets
        self.fields['appointment'].queryset = AppointmentDetails.objects.none()
        self.fields['completed_patient'].queryset = AppointmentDetails.objects.none()

        # Inject presets as choices
        self.fields['notes_history'].choices  = [(v, v) for v in HISTORY_PRESETS]
        self.fields['notes_symptoms'].choices = [(v, v) for v in SYMPTOM_PRESETS]
        self.fields['notes_findings'].choices = [(v, v) for v in FINDINGS_PRESETS]
        self.fields['general_advice'].choices = [(v, v) for v in GENERAL_ADVICE_PRESETS]

        # Populate appointments based on doctor
        doctor_obj = getattr(user, 'doctor', None)
        if not doctor_obj and self.data.get('doctor'):
            try:
                doctor_obj = Doctor.objects.get(id=int(self.data.get('doctor')), hospital=hospital)
            except Exception:
                doctor_obj = None

        if doctor_obj and hospital:
            today = timezone.now().date()
            qs = AppointmentDetails.objects.filter(
                hospital=hospital,
                doctor=doctor_obj,
                appointment_on=today
            )
            self.fields['appointment'].queryset = qs.filter(completed=AppointmentDetails.STATUS_IN_QUEUE)
            self.fields['completed_patient'].queryset = qs.filter(completed=AppointmentDetails.STATUS_DONE)

    def _join_list(self, val):
        
        if isinstance(val, (list, tuple)):
            return ', '.join(val)
        return val

    def clean_notes_history(self):
        print(self.cleaned_data.get('notes_history'))
        return self._join_list(self.cleaned_data.get('notes_history'))

    def clean_notes_symptoms(self):
        return self._join_list(self.cleaned_data.get('notes_symptoms'))

    def clean_notes_findings(self):
        return self._join_list(self.cleaned_data.get('notes_findings'))

    def clean_general_advice(self):
        return self._join_list(self.cleaned_data.get('general_advice'))

    def _join_list(self, field_name):
        val = self.cleaned_data.get(field_name)
        if isinstance(val, (list, tuple)):
            return ', '.join(val)
        return val

    def clean_notes_history(self):
        return self._join_list('notes_history')

    def clean_notes_symptoms(self):
        return self._join_list('notes_symptoms')

    def clean_notes_findings(self):
        return self._join_list('notes_findings')

    def clean_general_advice(self):
        return self._join_list('general_advice')



# Custom choice field for patient selection omitted for brevity
class PrescriptionDetailForm(forms.ModelForm):
    """Form for PrescriptionDetails, with AJAX-powered drug autocomplete."""
    # ---- Manual prescription formset for AI wizard ----
    

    
    class Meta:
        model = PrescriptionDetails
        fields = ['drug_name', 'composition', 'dosage', 'frequency', 'duration', 'food_order']
        widgets = {
            'composition': forms.Textarea(attrs={'rows': 1, 'class': 'form-control'}),
            'dosage':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dosage…'}),
            'frequency':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Frequency…'}),
            'duration':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Duration…'}),
            'food_order':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Food order…'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔹 drug_name required (we need at least name)
        self.fields['drug_name'] = forms.CharField(
            widget=forms.TextInput(
                attrs={
                    'class': 'form-control drug-name-autocomplete',
                    'placeholder': 'Type drug name...',
                    'autocomplete': 'off',
                }
            ),
            label='Drug',
            required=True,
        )

        # 🔹 make the rest optional for the formset validation
        self.fields['composition'].required = False
        self.fields['dosage'].required = False
        self.fields['frequency'].required = False
        self.fields['duration'].required = False
        self.fields['food_order'].required = False

        # Populate presets for dosage, frequency, duration
        for field_name in ['dosage', 'frequency', 'duration']:
            presets = UserPreset.objects.filter(user=user, field_name=field_name)
            preset_values = [p.value for p in presets]

            self.fields[field_name].widget.attrs['list'] = f"datalist-{field_name}"
            self.fields[field_name].widget.attrs['data-presets'] = ",".join(preset_values)

ManualDetailFormSet = formset_factory(
        PrescriptionDetailForm,
        extra=1,        # start with one row
        can_delete=True
    )
        

