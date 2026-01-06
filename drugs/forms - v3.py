from django import forms
from django.forms import formset_factory


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



DrugFormSet = formset_factory(DrugForm, extra=1, can_delete=True)