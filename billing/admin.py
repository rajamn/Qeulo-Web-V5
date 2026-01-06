from django.contrib import admin
from billing.models import PaymentMaster, PaymentTransaction
# Register your models here.
@admin.register(PaymentMaster)
class PaymentMasterAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'total_amount', 'paid_on', 'collected_by', 'hospital')
    search_fields = ('patient__patient_name', 'contact__mobile_num')
    list_filter = ('paid_on', 'hospital')

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('payment', 'doctor', 'service', 'amount', 'pay_type', 'hospital', 'created_at')
    list_filter = ('pay_type', 'hospital', 'created_at')
    search_fields = ('doctor__doctor_name', 'service__service_name')

class PaymentTransactionInline(admin.TabularInline):
    model = PaymentTransaction
    extra = 0