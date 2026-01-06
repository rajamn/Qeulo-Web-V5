from core.models import Role

roles = ['admin', 'reception', 'doctor']
for role_name in roles:
    Role.objects.get_or_create(role_name=role_name)

print("✅ Roles created or already exist.")
from core.models import Role

