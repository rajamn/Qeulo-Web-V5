# core/utils/roles.py
from functools import wraps
from django.http import HttpResponseForbidden

# Role ranking (higher = more powerful)
ROLE_HIERARCHY = {
    "Reception": 1,
    "Accountant": 2,
    "Doctor": 3,
    "hospital_admin": 4,
}

def user_has_role(user, *allowed_roles):
    """
    Checks if the user's role is at least as powerful as the lowest allowed role.
    hospital_admin always passes.
    """
    if not getattr(user, "is_authenticated", False):
        return False

    user_role = getattr(getattr(user, "role", None), "role_name", None)
    if user_role is None:
        return False

    # hospital_admin always passes
    if user_role == "hospital_admin":
        return True

    # otherwise check against allowed roles
    return user_role in allowed_roles
