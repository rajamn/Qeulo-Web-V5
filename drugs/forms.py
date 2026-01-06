from django import forms
from django.forms import formset_factory, inlineformset_factory
from .models import Drug
from .models import DrugTemplate, Drug
from prescription.models import PrescriptionMaster, PrescriptionDetails
from prescription.forms import PrescriptionDetailForm


# create a DrugFormSet here so you can import it directly:


class DrugForm(forms.Form):
    drug_name_new = forms.CharField(
        widget=forms.TextInput(attrs={
                'class': 'form-control drug-name-autocomplete',
            'placeholder': 'Enter or select drug'
        })
    )
    composition = forms.CharField(
        widget=forms.TextInput(attrs={
                'class': 'form-control composition-input',
            'placeholder': ''
        })
    )
    dosage = forms.CharField(
        widget=forms.TextInput(attrs={
                'class': 'form-control dosage-select',
            'placeholder': ''
        })
    )
    frequency = forms.CharField(
        widget=forms.TextInput(attrs={
                'class': 'form-control frequency-select',
            'placeholder': ''
        })
    )
    duration = forms.CharField(
        widget=forms.TextInput(attrs={
                'class': 'form-control duration-select',
            'placeholder': ''
        })
    )




class DrugFilterForm(forms.Form):
    q = forms.CharField(required=False, label='Search')
    show_global = forms.BooleanField(required=False, initial=False, label='Global')
    show_hospital = forms.BooleanField(required=False, initial=True, label='Hospital')
    show_doctor = forms.BooleanField(required=False, initial=True, label='Doctor')


# DrugFormSet = formset_factory(DrugForm, extra=1, can_delete=True)
DetailInlineFormSet = inlineformset_factory(
    parent_model=PrescriptionMaster,
    model=PrescriptionDetails,
    form=PrescriptionDetailForm,
    fk_name='prescription',   # only if your FK field is named `prescription` (it is)
    extra=1,
    can_delete=True,
)


class DrugAddForm(forms.ModelForm):
    class Meta:
        model = Drug
        fields = [
            'drug_name',
            'composition',
            'dosage',
            'frequency',
            'duration',
            'uses',
            'side_effects',
            'manufacturer',
        ]
        widgets = {
            'drug_name': forms.TextInput(attrs={'class': 'form-control'}),
            'composition': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'dosage': forms.TextInput(attrs={'class': 'form-control'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'uses': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'side_effects': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        drug = super().save(commit=False)
        if self.doctor:
            drug.added_by_doctor = self.doctor
            drug.hospital = self.doctor.hospital
        if commit:
            drug.save()
        return drug




class DrugTemplateForm(forms.ModelForm):
    drugs = forms.ModelMultipleChoiceField(
        queryset=Drug.objects.all().order_by('drug_name'),
        widget=forms.SelectMultiple(attrs={'size': 10, 'class': 'form-control'}),
        required=True,
        label="Select Drugs"
    )

    class Meta:
        model = DrugTemplate
        fields = ['name', 'drugs']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
