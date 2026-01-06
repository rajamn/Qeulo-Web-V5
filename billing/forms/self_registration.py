from django import forms
from billing.models import PaymentMaster, PaymentTransaction
from django.forms import modelformset_factory
from doctors.models import Doctor
from services.models import Service
from decimal import Decimal


# ✅ Define this first
class SelfPaymentTransactionForm(forms.ModelForm):
    class Meta:
        model = PaymentTransaction
        fields = ['service', 'pay_type', 'amount']  
        widgets = {
            'pay_type': forms.Select(attrs={'placeholder': 'Payment type'}),
            'amount': forms.NumberInput(attrs={'placeholder': 'Amount'}),
        }

    def __init__(self, *args, **kwargs):
        hospital_id = kwargs.pop('hospital_id', None)
        public = kwargs.pop('public', False)
        super().__init__(*args, **kwargs)

        if hospital_id:
            self.fields['service'].queryset = Service.objects.filter(hospital_id=hospital_id)

            # Try to get Consultation service
            # Default to "Consultation" (uses correct field names)
            consultation = Service.objects.filter(
                hospital_id=hospital_id,
                service_name__iexact="Consultation"
            ).first()

            # Set defaults only for new/unbound forms with no instance values
            if consultation and not self.is_bound:
                if not getattr(self.instance, 'service_id', None) and 'service' not in self.initial:
                    self.initial['service'] = consultation.id
                if not getattr(self.instance, 'amount', None) and 'amount' not in self.initial:
                    self.initial['amount'] = consultation.service_fees
    
            # ✅ Only this line handles slug (public) logic
            if public:
                self.fields['pay_type'].initial = 'Due'
    def clean(self):
        cleaned = super().clean()
        pay_type = cleaned.get('pay_type')

        # 🔹 Enforce Review = 0 amount
        if pay_type == 'Review':
            cleaned['amount'] = Decimal('0.00')

        return cleaned