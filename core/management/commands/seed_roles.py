# core/management/commands/seed_roles.py
from core.management.commands._base_seed import BaseSeedCommand
from core.models import Role

class Command(BaseSeedCommand):
    help = "Seed default roles"

    def seed(self):
        defaults = ['Reception', 'Doctor', 'Administrator']
        for rn in defaults:
            obj, created = Role.objects.get_or_create(role_name=rn)
            if created:
                self.stdout.write(self.style.SUCCESS(f"• Created role {rn}"))
            else:
                self.stdout.write(f"• Role {rn} already existed")
