from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import Service

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('service_name', 'service_fees', 'hospital', 'created_at')
    search_fields = ('service_name',)
    list_filter = ('hospital',)

