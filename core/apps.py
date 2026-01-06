# core/apps.py
from django.apps import AppConfig, apps
from django.db.models.signals import post_migrate

def create_default_roles(sender, **kwargs):
    """Ensure core roles exist after migration."""
    Role = apps.get_model('core', 'Role')
    default_roles = ['Reception', 'Doctor', 'hospital_admin', 'Accountant']
    for role_name in default_roles:
        Role.objects.get_or_create(role_name=role_name)
    print("✅ Default roles ensured via CoreConfig.")


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Register signal handlers (doctor → user sync, hospital admin creation, etc.)
        import core.signals

        # Auto-create roles after migrations
        post_migrate.connect(create_default_roles, sender=self)
