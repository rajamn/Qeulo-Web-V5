# core/management/commands/seed_users.py

import sys
from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings

from core.management.commands._base_seed import BaseSeedCommand


class Command(BaseSeedCommand):
    help = "Seed a set of HospitalUser accounts for a given hospital"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--hospital-phone', help="Phone number of the hospital to add users to")
        group.add_argument('--hospital-id', type=int, help="ID of the hospital to add users to")

    def seed(self):
        Hospital     = apps.get_model('core', 'Hospital')
        HospitalUser = apps.get_model('core', 'HospitalUser')
        Role         = apps.get_model('core', 'Role')

        # lookup hospital
        lookup = (
            {'phone_num': self.options['hospital_phone']}
            if self.options.get('hospital_phone')
            else {'id': self.options['hospital_id']}
        )

        try:
            hospital = Hospital.objects.get(**lookup)
        except Hospital.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"No hospital found matching {lookup}"))
            sys.exit(1)

        user_data = [
            {"mobile_num": "9959223401", "role": "Administrator"},
            
        ]

        default_pw = getattr(settings, 'DEFAULT_USER_PASSWORD', 'changeme123')

        for entry in user_data:
            role_obj = Role.objects.get(role_name=entry['role'])
            mobile   = entry['mobile_num']

            user_qs = HospitalUser.objects.filter(mobile_num=mobile, hospital=hospital)

            if user_qs.exists():
                user = user_qs.first()
                updated_fields = []

                # Reset password
                user.set_password(default_pw)
                updated_fields.append("password")

                # Update role if changed
                if user.role_id != role_obj.id:
                    user.role = role_obj
                    updated_fields.append("role")

                user.save()
                self.stdout.write(self.style.NOTICE(
                    f"Updated {mobile}: {', '.join(updated_fields)}"
                ))

            else:
                HospitalUser.objects.create_user(
                    mobile_num=mobile,
                    user_name=mobile,  # sensible fallback
                    hospital=hospital,
                    role=role_obj
                )
                self.stdout.write(self.style.SUCCESS(
                    f"Created user {mobile} as {entry['role']}"
                ))

        self.stdout.write(self.style.SUCCESS("✅ Seed users complete"))
