from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from core.models import Hospital

class Command(BaseCommand):
    help = "Create a hospital user and assign role (admin/doctor/reception)"

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the user')
        parser.add_argument('password', type=str, help='Password for the user')
        parser.add_argument('email', type=str, help='Email address')
        parser.add_argument('mobile', type=str, help='Mobile number')
        parser.add_argument('hospital_id', type=int, help='Hospital ID')
        parser.add_argument('role', type=str, choices=['admin', 'doctor', 'reception'], help='Role for the user')

    def handle(self, *args, **kwargs):
        username = kwargs['username']
        password = kwargs['password']
        email = kwargs['email']
        mobile = kwargs['mobile']
        hospital_id = kwargs['hospital_id']
        role = kwargs['role']

        try:
            hospital = Hospital.objects.get(id=hospital_id)
        except Hospital.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Hospital with ID {hospital_id} does not exist."))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f"❌ User '{username}' already exists."))
            return

        user = User.objects.create_user(username=username, password=password, email=email)
        user.first_name = mobile  # optional usage of `mobile` for now
        user.save()

        group, created = Group.objects.get_or_create(name=role)
        user.groups.add(group)

        self.stdout.write(self.style.SUCCESS(f"✅ User '{username}' created and added to group '{role}' for hospital '{hospital.hospital_name}'"))
