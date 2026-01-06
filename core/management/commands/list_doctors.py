from doctors.models import Doctor

doctors = Doctor.objects.all()

if doctors.exists():
    print("👨‍⚕️ Doctor ID → Name list:\n")
    for doc in doctors:
        print(f"ID={doc.id:>2} → {doc.doctor_name}")
else:
    print("❌ No doctors found.")
