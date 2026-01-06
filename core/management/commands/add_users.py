from core.models import Role, HospitalUser, Hospital

doctor_role = Role.objects.get(role_name="doctor")
receptionist_role = Role.objects.get(role_name="reception")
admin_role = Role.objects.get(role_name="admin")
# User data
user_data = [
{"mobile_num": "8197441179", "user_name": "prabhath", "password": "prabhath123", "role": doctor_role},
{"mobile_num": "9848199567", "user_name": "krishna", "password": "prasad123", "role": doctor_role},
{"mobile_num": "8008222722", "user_name": "grace", "password": "grace123", "role": receptionist_role},
{"mobile_num": "7207064678", "user_name": "rajam", "password": "rajam123", "role": admin_role},
]
# Use lowercase role names based on your earlier creation

# Get the hospital instance
hospital = Hospital.objects.get(hospital_name="Six Sigma PMC")

user_data = [
{"mobile_num": "8197441179", "user_name": "prabhath", "password": "prabhath123", "role": doctor_role},
{"mobile_num": "9848199567", "user_name": "krishna", "password": "prasad123", "role": doctor_role},
{"mobile_num": "8008222722", "user_name": "grace", "password": "grace123", "role": receptionist_role},
{"mobile_num": "7207064678", "user_name": "rajam", "password": "rajam123", "role": admin_role},
]
# Use lowercase role names based on your earlier creation

# Create users
for user in user_data:
    existing_user = HospitalUser.objects.filter(mobile_num=user["mobile_num"]).first()
    if existing_user:
        # 🔄 Update role if it's different
        if existing_user.role != user["role"]:
            existing_user.role = user["role"]
            existing_user.save()
            print(f"Updated role for {user['user_name']}")
        else:
            print(f"User {user['user_name']} already has correct role, skipping.")
    else:
        HospitalUser.objects.create_user(
            mobile_num=user["mobile_num"],
            user_name=user["user_name"],
            password=user["password"],
            hospital=hospital,
            role=user["role"],
        )
        print(f"✅ Created user {user['user_name']}")
    HospitalUser.objects.update(must_change_password=True)
    print("🔐 All users marked to change password.")
