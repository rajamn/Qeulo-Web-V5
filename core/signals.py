# core/signals.py

from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.conf import settings
from core.models import Role, Hospital, HospitalUser
from doctors.models import Doctor


# -------------------------------------------------------------
# 1️⃣ Ensure all default roles exist after migrations
# -------------------------------------------------------------
@receiver(post_migrate)
def ensure_default_roles(sender, **kwargs):
    """Create core roles after migrations if they do not exist."""
    if sender.name == "core":
        default_roles = ["hospital_admin", "Doctor", "Reception", "Accountant"]
        for role_name in default_roles:
            Role.objects.get_or_create(role_name=role_name)
        print("✅ Default roles ensured.")


# -------------------------------------------------------------
# 2️⃣ Create a default Hospital Admin when a Hospital is created
# -------------------------------------------------------------
@receiver(post_save, sender=Hospital)
def create_hospital_admin(sender, instance, created, **kwargs):
    """Auto-create a hospital_admin user for each new hospital."""
    if created:
        admin_role, _ = Role.objects.get_or_create(role_name="hospital_admin")
        default_pw = getattr(settings, "DEFAULT_USER_PASSWORD", "Admin$123")

        user = HospitalUser.objects.create_user(
            mobile_num=instance.phone_num,
            user_name=f"{instance.hospital_name} Admin",
            password=default_pw,
            hospital=instance,
            role=admin_role,
            is_staff=True,
        )
        user.must_change_password = True
        user.save(update_fields=["must_change_password"])
        print(f"🏥 Created default hospital admin for {instance.hospital_name}")


# -------------------------------------------------------------
# 3️⃣ Create or update HospitalUser automatically when Doctor is added
# -------------------------------------------------------------
@receiver(post_save, sender=Doctor)
def create_or_update_doctor_user(sender, instance, created, **kwargs):
    """Auto-create or update a HospitalUser for each Doctor."""
    doctor_role, _ = Role.objects.get_or_create(role_name="Doctor")
    default_pw = getattr(settings, "DEFAULT_USER_PASSWORD", "changeme123")

    if created:
        # On first creation, create a HospitalUser linked to this doctor
        user = HospitalUser.objects.create_user(
            mobile_num=instance.doc_mobile_num,
            user_name=instance.doctor_name,
            password=default_pw,
            hospital=instance.hospital,
            role=doctor_role,
        )
        user.doctor = instance
        user.must_change_password = True
        user.save(update_fields=["doctor", "must_change_password"])
        print(f"👨‍⚕️ Created doctor user for {instance.doctor_name}")

    else:
        # On updates, sync relevant fields
        user = HospitalUser.objects.filter(mobile_num=instance.doc_mobile_num).first()
        if user:
            changed = False
            if user.user_name != instance.doctor_name:
                user.user_name = instance.doctor_name
                changed = True
            if user.hospital_id != instance.hospital_id:
                user.hospital_id = instance.hospital_id
                changed = True
            if user.role_id != doctor_role.id:
                user.role_id = doctor_role.id
                changed = True
            if getattr(user, "doctor_id", None) != instance.id:
                user.doctor_id = instance.id
                changed = True
            if changed:
                user.save(update_fields=["user_name", "hospital", "role", "doctor"])
                print(f"🔄 Synced doctor user for {instance.doctor_name}")
