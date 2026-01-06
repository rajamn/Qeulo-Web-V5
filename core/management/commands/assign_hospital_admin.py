# core/management/commands/assign_hospital_admin.py
from django.core.management.base import BaseCommand, CommandError
from core.models import HospitalUser, Role, Hospital
#python manage.py assign_hospital_admin 9876543210 12

class Command(BaseCommand):
    help = "Assigns the 'hospital_admin' role to a user given their mobile number and hospital ID"

    def add_arguments(self, parser):
        parser.add_argument('mobile_num', type=str, help="Mobile number of the user")
        parser.add_argument('hospital_id', type=int, help="Hospital ID")

    def handle(self, *args, **options):
        mobile_num = options['mobile_num']
        hospital_id = options['hospital_id']

        try:
            # ✅ Fetch user and hospital
            user = HospitalUser.objects.get(mobile_num=mobile_num, hospital_id=hospital_id)
            hospital = Hospital.objects.get(pk=hospital_id)

            # ✅ Ensure role exists
            role, _ = Role.objects.get_or_create(role_name='hospital_admin')

            # ✅ Assign role
            user.role = role
            user.save(update_fields=['role'])

            self.stdout.write(self.style.SUCCESS(
                f"✅ User '{user.user_name}' ({mobile_num}) assigned as hospital_admin for '{hospital.hospital_name}'"
            ))

        except HospitalUser.DoesNotExist:
            raise CommandError(f"❌ User with mobile {mobile_num} and hospital_id {hospital_id} not found.")
        except Hospital.DoesNotExist:
            raise CommandError(f"❌ Hospital with id {hospital_id} not found.")
        except Exception as e:
            raise CommandError(f"❌ Unexpected error: {e}")
