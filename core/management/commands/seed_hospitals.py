# core/management/commands/seed_hospitals.py
from core.management.commands._base_seed import BaseSeedCommand
from core.models import Hospital

class Command(BaseSeedCommand):
    help = "Seed default hospital data"

    def seed(self):
        hospital_data = [
            {
                "hospital_name": "Bhadrakali Nursing Home",
                "phone_num":     "8333831892",
                "street":        "Kishanpura",
                "city":          "Warangal",
                "state":         "Telangana",
                "pincode":       "506001",
                "email":         "sribhadrakalidiagnostics@gmail.com"
            },
            {
                "hospital_name": "Six Sigma PMC",
                "phone_num":     "8008222722",
                "street":        "Sheshadri Marg",
                "city":          "Hyderabad",
                "state":         "Telangana",
                "pincode":       "500001",
                "email":         "sixsigma@example.com"
            },
            {
                "hospital_name": "Naidu Eye Clinic",
                "phone_num":     "9494043693",
                "street":        "Madina Guda",
                "city":          "Hyderabad",
                "state":         "Telangana",
                "pincode":       "500050",
                "email":         "naidueye@example.com"
            },
            {
                "hospital_name": "Abhinav Eyecare",
                "phone_num":     "9154755802",
                "street":        "Boduppal",
                "city":          "Hyderabad",
                "state":         "Telangana",
                "pincode":       "500092",
                "email":         "abhinav@example.com"
            },
        ]

        for data in hospital_data:
            obj, created = Hospital.objects.get_or_create(
                email=data["email"],
                defaults={
                    "hospital_name": data["hospital_name"],
                    "phone_num":     data["phone_num"],
                    "street":        data["street"],
                    "city":          data["city"],
                    "state":         data["state"],
                    "pincode":       data["pincode"],
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"• Created hospital: {obj.hospital_name} ({obj.email})"
                ))
            else:
                self.stdout.write(
                    f"• Hospital already existed: {obj.hospital_name} ({obj.email})"
                )
