from billing.models import Service
from core.models import Hospital

# Define the default service list
default_services = [
    {"service_name": "Consultation", "service_fees": 400},
    {"service_name": "Injection", "service_fees": 100},
    {"service_name": "Dressing", "service_fees": 300},
    {"service_name": "GRBS", "service_fees": 100},
    {"service_name": "BP Charges", "service_fees": 50},
    {"service_name": "Lab Charges", "service_fees": 500},
    {"service_name": "Vaccination", "service_fees": 300},
    {"service_name": "POP CAST", "service_fees": 4000},
    {"service_name": "Procedure", "service_fees": 500},
    {"service_name": "IV Fluids", "service_fees": 500},
]

# Set to True to apply to all hospitals, or False to use specific ID
apply_to_all = False
target_hospital_ids = [1]  # Replace with actual IDs or set to [] if apply_to_all=True

# Fetch hospital list
if apply_to_all:
    hospitals = Hospital.objects.all()
else:
    hospitals = Hospital.objects.filter(id__in=target_hospital_ids)

# Add services to each hospital
for hospital in hospitals:
    print(f"\n👉 Processing hospital: {hospital.hospital_name} (ID: {hospital.id})")
    for service_data in default_services:
        service, created = Service.objects.get_or_create(
            service_name=service_data["service_name"],
            hospital=hospital,
            defaults={"service_fees": service_data["service_fees"]}
        )
        if created:
            print(f"   ✅ Added: {service.service_name}")
        else:
            print(f"   ⚠️ Exists: {service.service_name}")
