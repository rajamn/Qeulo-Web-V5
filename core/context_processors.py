def global_sidebar_context(request):
    hospital = getattr(request.user, "hospital", None)

    return {
        "current_hospital": hospital,
        "current_user": request.user,
        "active_menu": "",      # default to blank
    }
