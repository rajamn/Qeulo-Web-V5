def get_display_name(user):
    """Return a safe display name for any user model."""
    if hasattr(user, "user_name") and user.user_name:
        return user.user_name
    if hasattr(user, "email") and user.email:
        return user.email
    if hasattr(user, "get_username"):
        return user.get_username()
    return str(user)


def collected_by_label(user):
    """
    Safely return a readable name for the collected_by field.
    Handles HospitalUser, superuser, and public (anonymous) cases.
    """
    # HospitalUser: prefer display_name or user_name
    if hasattr(user, "display"):
        return user.display

    # Django User fallback (e.g. superuser / staff)
    if hasattr(user, "get_username"):
        return user.get_username()

    # Anonymous or unexpected user
    return "Online"
