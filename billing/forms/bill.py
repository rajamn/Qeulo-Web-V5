# billing/forms.py
from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from billing.models import PaymentMaster, PaymentTransaction
from patients.models import Patient
from doctors.models import Doctor
from services.models import Service

class PaymentMasterForm(forms.ModelForm):
    class Meta:
        model = PaymentMaster
        fields = ["paid_on"]  # ← EXACTLY your fields on the form

        
class PaymentTransactionForm(forms.ModelForm):
    class Meta:
        model  = PaymentTransaction
        fields = ["doctor", "service", "pay_type", "amount"]  # ← EXACTLY your row fields
    
    def __init__(self, *args, hospital=None, **kwargs):
        super().__init__(*args, **kwargs)
        if hospital is not None:
            self.fields["doctor"].queryset  = Doctor.objects.filter(hospital=hospital)
            self.fields["service"].queryset = (Service.objects.filter(hospital=hospital)
    .exclude(service_name__iexact="Consultation").order_by("service_name")
)


class TxBaseFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        has_line = False
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get("DELETE", False):
                has_line = True
                amt = form.cleaned_data.get("amount") or 0
                if amt <= 0:
                    form.add_error("amount", "Amount must be > 0")
        if not has_line:
            raise forms.ValidationError("Add at least one service line.")

PaymentTransactionFormSet = inlineformset_factory(
    PaymentMaster,
    PaymentTransaction,
    form=PaymentTransactionForm,
    fields=["doctor","service","pay_type","amount"],
    can_delete=True,
    extra=1,
    formset=TxBaseFormSet
)

def limit_tx_queryset(formset, hospital):
    for f in formset.forms:
        f.fields["doctor"].queryset  = Doctor.objects.filter(hospital=hospital)
        f.fields["service"].queryset = Service.objects.filter(hospital=hospital).order_by("service_name")
