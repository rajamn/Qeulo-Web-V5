
import os
import django
import random
from datetime import date
from faker import Faker

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quelo_backend.settings')
django.setup()

from core.models import Hospital, Contact
from patients.models import Patient
from doctors.models import Doctor
from services.models import Service
from billing.models import PaymentMaster, PaymentTransaction
from appointments.models import AppointmentDetails
from appointments.utils import get_next_queue_position
from utils.eta_calculator import calculate_eta_time
from patients.utils import generate_token_string

fake = Faker()

hospital_id = 1
hospital = Hospital.objects.get(id=hospital_id)
STATUS_DONE = 2
service_name = "Consultation"

# Payment data
payment_data = [{'patient_name': 'SanikaAsegaonkar', 'mobile_num': 1233401382,  'doctor_name': 'Dr. Y. S. R. Shanthi Navyatha', 'service_name': 'Consultation', 'pay_type': 'UPI', 'amount': 500, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Srushti', 'mobile_num': 1687944757, 'appointment_on': datetime.date(2025, 7, 15), 'doctor_name': 'Dr. P. Sai  Kumar', 'service_name': 'Consultation', 'pay_type': 'UPI', 'amount': 300, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Saithilak', 'mobile_num': 1718887789, 'appointment_on': datetime.date(2025, 7, 17), 'doctor_name': 'Dr. Francis Sridhar Katumalla', 'service_name': 'Consultation', 'pay_type': 'UPI', 'amount': 600, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Rathod prathapsingh', 'mobile_num': 1136264240, 'appointment_on': datetime.date(2025, 7, 16), 'doctor_name': 'Dr. Prabhath Kiran Reddy', 'service_name': 'Consultation', 'pay_type': 'Other', 'amount': 600, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Mohammed Zohaib Ahmed', 'mobile_num': 1425895815, 'appointment_on': datetime.date(2025, 7, 15), 'doctor_name': 'Dr. Francis Sridhar Katumalla', 'service_name': 'Consultation', 'pay_type': 'Other', 'amount': 400, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Venkatesh gonugunta', 'mobile_num': 1014176485, 'appointment_on': datetime.date(2025, 7, 15), 'doctor_name': 'Dr. P. Sai  Kumar', 'service_name': 'Consultation', 'pay_type': 'Other', 'amount': 400, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Vardhan Reddy', 'mobile_num': 1796629311, 'appointment_on': datetime.date(2025, 7, 15), 'doctor_name': 'Dr. A. Kranthi Kiran', 'service_name': 'Consultation', 'pay_type': 'Other', 'amount': 400, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Madhulatha', 'mobile_num': 1972032349, 'appointment_on': datetime.date(2025, 7, 15), 'doctor_name': 'Dr. A. Kranthi Kiran', 'service_name': 'Consultation', 'pay_type': 'UPI', 'amount': 500, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Manojkumar', 'mobile_num': 1861986961, 'appointment_on': datetime.date(2025, 7, 15), 'doctor_name': 'Dr. DVS Pratap', 'service_name': 'Consultation', 'pay_type': 'Card', 'amount': 400, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Adithya', 'mobile_num': 1260886780, 'appointment_on': datetime.date(2025, 7, 17), 'doctor_name': 'Dr. Prabhath Kiran Reddy', 'service_name': 'Consultation', 'pay_type': 'Other', 'amount': 500, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Vamshinayak', 'mobile_num': 1778098465, 'appointment_on': datetime.date(2025, 7, 17), 'doctor_name': 'Dr. DVS Pratap', 'service_name': 'Consultation', 'pay_type': 'Card', 'amount': 500, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Trushant', 'mobile_num': 1955780886, 'appointment_on': datetime.date(2025, 7, 16), 'doctor_name': 'Dr. DVS Pratap', 'service_name': 'Consultation', 'pay_type': 'Cash', 'amount': 300, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Mohd Abdul Aziz', 'mobile_num': 1603101015, 'appointment_on': datetime.date(2025, 7, 15), 'doctor_name': 'Dr. Y. S. R. Shanthi Navyatha', 'service_name': 'Consultation', 'pay_type': 'Cash', 'amount': 400, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Uday', 'mobile_num': 1819575825, 'appointment_on': datetime.date(2025, 7, 15), 'doctor_name': 'Dr. A. Kranthi Kiran', 'service_name': 'Consultation', 'pay_type': 'Other', 'amount': 600, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Anmisha', 'mobile_num': 1979171353, 'appointment_on': datetime.date(2025, 7, 16), 'doctor_name': 'Dr. V. Krishna Prasad', 'service_name': 'Consultation', 'pay_type': 'UPI', 'amount': 300, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Harsha Vardhini', 'mobile_num': 1230140490, 'appointment_on': datetime.date(2025, 7, 15), 'doctor_name': 'Dr. Harish Goutham Medipati', 'service_name': 'Consultation', 'pay_type': 'Cash', 'amount': 500, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Mohammad Hassan', 'mobile_num': 1701393073, 'appointment_on': datetime.date(2025, 7, 15), 'doctor_name': 'Dr. Harish Goutham Medipati', 'service_name': 'Consultation', 'pay_type': 'Other', 'amount': 300, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Satish', 'mobile_num': 1788642514, 'appointment_on': datetime.date(2025, 7, 15), 'doctor_name': 'Dr. Y. S. R. Shanthi Navyatha', 'service_name': 'Consultation', 'pay_type': 'Other', 'amount': 300, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Sunay Reddy', 'mobile_num': 1649580666, 'appointment_on': datetime.date(2025, 7, 15), 'doctor_name': 'Dr. Y. S. R. Shanthi Navyatha', 'service_name': 'Consultation', 'pay_type': 'Cash', 'amount': 300, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Bhargava Sai', 'mobile_num': 1477166766, 'appointment_on': datetime.date(2025, 7, 17), 'doctor_name': 'Dr. P. Sai  Kumar', 'service_name': 'Consultation', 'pay_type': 'UPI', 'amount': 500, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Mohammed abdul Mannan', 'mobile_num': 1895606477, 'appointment_on': datetime.date(2025, 7, 15), 'doctor_name': 'Dr. DVS Pratap', 'service_name': 'Consultation', 'pay_type': 'Card', 'amount': 500, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Hassan Mahabubur', 'mobile_num': 1294218975, 'appointment_on': datetime.date(2025, 7, 16), 'doctor_name': 'Dr. Francis Sridhar Katumalla', 'service_name': 'Consultation', 'pay_type': 'Other', 'amount': 400, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Meghana', 'mobile_num': 1128486883, 'appointment_on': datetime.date(2025, 7, 16), 'doctor_name': 'Dr. Prabhath Kiran Reddy', 'service_name': 'Consultation', 'pay_type': 'Other', 'amount': 600, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Deevenkumar', 'mobile_num': 1105370452, 'appointment_on': datetime.date(2025, 7, 17), 'doctor_name': 'Dr. Francis Sridhar Katumalla', 'service_name': 'Consultation', 'pay_type': 'Cash', 'amount': 400, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}, {'patient_name': 'Aniket', 'mobile_num': 1786343641, 'appointment_on': datetime.date(2025, 7, 17), 'doctor_name': 'Dr. DVS Pratap', 'service_name': 'Consultation', 'pay_type': 'Cash', 'amount': 500, 'paid_on': '2025-07-15', 'collected_by': 'Reception1', 'hospital_id': 1}]

for i, entry in enumerate(payment_data, start=1):
    try:
        doctor = Doctor.objects.get(doctor_name=entry['doctor_name'], hospital=hospital)
        service = Service.objects.get(service_name=service_name, hospital=hospital)
        contact = Contact.objects.get(mobile_num=entry['mobile_num'], hospital=hospital)
        patient = Patient.objects.get(contact=contact, patient_name=entry['patient_name'], hospital=hospital)

        # Create PaymentMaster
        payment = PaymentMaster.objects.create(
            mobile_num=entry['mobile_num'],
            patient=patient,
            total_amount=0,
            collected_by=entry['collected_by'],
            hospital=hospital
        )

        # Create PaymentTransaction (no paid_on used)
        txn = PaymentTransaction.objects.create(
            payment=payment,
            doctor=doctor,
            service=service,
            pay_type=entry['pay_type'],
            amount=entry['amount'],
            patient=patient,
            hospital=hospital
        )

        payment.total_amount = txn.amount
        payment.save()

        # Create appointment for today
        today = date.today()
        appointment = AppointmentDetails.objects.create(
            appointment_on=today,
            doctor=doctor,
            patient=patient,
            mobile_num=entry['mobile_num'],
            payment=payment,
            token_num=generate_token_string(),
            que_pos=get_next_queue_position(doctor=doctor, date=today, hospital=hospital),
            eta=calculate_eta_time(doctor.start_time, doctor.average_time_minutes, get_next_queue_position(doctor, today, hospital)),
            completed=STATUS_DONE,
            hospital=hospital
        )

        print(f"✅ Payment + appointment saved for: {entry['patient_name']}")

    except Exception as e:
        print(f"❌ Error for {entry['patient_name']}: {str(e)}")

print("✅ Seeding completed with no paid_on usage.")
