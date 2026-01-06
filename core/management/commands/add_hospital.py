from core.models import Hospital

hospital_data = [
    {
        "hospital_name": "Six Sigma PMC",
        "phone_num": "8008222722",
        "street": "Sheshadri Marg",
        "city": "Hyderabad",
        "state": "Telangana",
        "pincode": "500001",
        "email": "sixsigma@example.com"
    },
    {
        "hospital_name": "Naidu Eye Clinic",
        "phone_num": "9494043693",
        "street": "Madina Guda",
        "city": "Hyderabad",
        "state": "Telangana",
        "pincode": "500050",
        "email": "naidueye@example.com"
    },
    {
        "hospital_name": "Abhinav Eyecare",
        "phone_num": "9154755802",
        "street": "Boduppal",
        "city": "Hyderabad",
        "state": "Telangana",
        "pincode": "500092",
        "email": "abhinav@example.com"
    }
]

for data in hospital_data:
    Hospital.objects.get_or_create(email=data["email"], defaults=data)
