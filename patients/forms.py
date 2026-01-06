from django import forms
from patients.models import Contact,Patient
from django.core.validators import RegexValidator
from appointments.forms import AppointmentForm
from datetime import date,datetime
from typing import Tuple
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from patients.models import Contact, Patient

GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]

digits10 = RegexValidator(
    regex=r'^\d{10}$',
    message="Enter a 10-digit mobile number."
)


class PatientRegistrationForm(forms.ModelForm):
    """
    Patient registration form (supports both create & edit).
    Uses DOB instead of age fields and auto-upserts Contact + Patient.
    """

    # 🗓️ DOB with correct type/format
    dob = forms.DateField(
    required=False,
    label="Date of Birth",
    widget=forms.DateInput(
        attrs={
            "type": "text",  # ⛔️ Use text, not date
            "class": "form-control",
            "placeholder": "DD-MM-YYYY",
            "autocomplete": "off",
        },
        format="%d-%m-%Y",  # ✅ Display in DD-MM-YYYY
    ),
    input_formats=["%d-%m-%Y", "%Y-%m-%d"],  # ✅ Accept both formats
    help_text="Enter date in DD-MM-YYYY format",
)


    # 🧍 Contact info
    mobile_num = forms.CharField(
        max_length=10,
        validators=[digits10],
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
        label="Mobile Number",
    )

    contact_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
        label="Contact Name",
    )

    # 🩺 Patient info
    patient_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
        label="Patient Name",
    )
    gender = forms.ChoiceField(choices=GENDER_CHOICES)
    referred_by = forms.CharField(required=False, max_length=100, label="Referred By")

    class Meta:
        model = Patient
        fields = ["patient_name", "dob", "gender", "referred_by"]

    # ---------- Validation ----------

    def clean_mobile_num(self) -> str:
        raw = (self.cleaned_data.get("mobile_num") or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if len(digits) != 10:
            raise ValidationError("Enter a valid 10-digit mobile number.")
        return digits

    def clean_dob(self):
        dob = self.cleaned_data.get("dob")
        if dob and dob > date.today():
            raise ValidationError("Date of birth cannot be in the future.")
        return dob


    def clean_contact_name(self):
        return (self.cleaned_data.get("contact_name") or "").strip()

    def clean_patient_name(self):
        return (self.cleaned_data.get("patient_name") or "").strip()

    def clean_referred_by(self):
        return (self.cleaned_data.get("referred_by") or "").strip()

    def clean(self):
        cleaned = super().clean()
        # Add any cross-field validation here (if required)
        return cleaned

    # ---------- Save Logic ----------

    def save(self, hospital) -> Tuple[Contact, Patient]:
        """
        Upsert Contact and Patient based on cleaned_data.
        Works for both new and existing records.
        """
        if hospital is None:
            raise ValueError("Hospital instance must be provided to save().")

        if not hasattr(self, "cleaned_data"):
            raise ValueError("Call is_valid() before save().")

        cd = self.cleaned_data

        # 1️⃣ Upsert Contact
        contact, _ = Contact.objects.get_or_create(
            mobile_num=cd["mobile_num"],
            hospital=hospital,
            defaults={"contact_name": cd["contact_name"]},
        )

        if contact.contact_name != cd["contact_name"]:
            contact.contact_name = cd["contact_name"]
            contact.save(update_fields=["contact_name"])

        # 2️⃣ Upsert Patient
        patient, created = Patient.objects.get_or_create(
            contact=contact,
            patient_name=cd["patient_name"],
            hospital=hospital,
            defaults={
                "dob": cd.get("dob"),
                "gender": cd["gender"],
                "referred_by": cd.get("referred_by") or "",
            },
        )

        # 3️⃣ Update existing patient if edited
        updated_fields = []
        for field in ["dob", "gender", "referred_by"]:
            new_val = cd.get(field)
            if getattr(patient, field) != new_val:
                setattr(patient, field, new_val)
                updated_fields.append(field)

        if updated_fields:
            patient.save(update_fields=updated_fields)

        return contact, patient


class PatientSearchForm(forms.Form):
    patient = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class':       'form-control form-control-sm',
            'id':          'patientSearch',
            'placeholder': 'Search by name or mobile…',
        })
    )
