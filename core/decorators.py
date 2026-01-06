from functools import wraps
from django.http import HttpResponseForbidden
from functools import wraps
from doctors.models import Doctor  # ← wherever your Doctor model lives


# @role_required("Doctor", "Reception")
# def view_appointments(request):
#     ...

def role_required(*allowed_roles, allow_superuser=True):
    """
    Usage:
        @role_required("doctor", "reception")
        @role_required("hospital_admin")
    
    Notes:
    - Case-insensitive
    - hospital_admin always allowed
    - Superuser allowed unless disabled
    """
    # Normalize allowed roles once
    allowed = {r.lower() for r in allowed_roles}

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user

            # Must be authenticated
            if not user.is_authenticated:
                return HttpResponseForbidden("Authentication required.")

            # Superuser bypass
            if allow_superuser and user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Extract user role safely
            role_obj = getattr(user, "role", None)
            role_name = getattr(role_obj, "role_name", None)

            if not role_name:
                return HttpResponseForbidden("Role not assigned.")

            role_name = role_name.lower()  # normalize

            # hospital_admin can do everything
            if role_name == "hospital_admin":
                return view_func(request, *args, **kwargs)

            # Regular role check
            if role_name in allowed:
                return view_func(request, *args, **kwargs)

            return HttpResponseForbidden("You do not have permission to access this page.")
        return _wrapped
    return decorator



def doctor_required(view_func):
    """
    Ensures the user is in the 'Doctor' role *and* has a corresponding Doctor record.
    If so, attaches the Doctor instance as `request.doctor`.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        # 1) role check
        if not user.is_authenticated or user.role.role_name != "Doctor":
            return HttpResponseForbidden("You must be a doctor to access this page.")
        # 2) lookup their Doctor profile
        try:
            doc = Doctor.objects.get(
                doc_mobile_num=user.mobile_num,
                hospital=user.hospital
            )
        except Doctor.DoesNotExist:
            return HttpResponseForbidden("No doctor profile found for this account.")
        # 3) stash it on the request
        request.doctor = doc
        return view_func(request, *args, **kwargs)
    return _wrapped


# in core/decorators.py
def hospital_admin_required(view_func):
    return role_required("hospital_admin")(view_func)

def administrator_required(view_func):
    return role_required("admin")(view_func)

def reception_required(view_func):
    return role_required("Reception")(view_func)

def accountant_required(view_func):
    return role_required("Accountant")(view_func)

