from django.core.exceptions import DisallowedHost

class IgnoreDisallowedHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except DisallowedHost:
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest("Invalid Host Header")



# core/middleware.py
from django.shortcuts import redirect
from .models import Hospital

def hospital_context_middleware(get_response):
    def middleware(request):
        rm = getattr(request, "resolver_match", None)
        slug = rm.kwargs.get("slug") if rm and rm.kwargs else None

        request.hospital = None
        if slug:
            hospital = Hospital.objects.filter(slug=slug).first()
            if not hospital:
                return redirect("login")  # or a branded 404
            request.hospital = hospital
            request.session["hospital_id"] = hospital.id
        else:
            hid = request.session.get("hospital_id")
            if hid:
                request.hospital = Hospital.objects.filter(id=hid).first()

        return get_response(request)
    return middleware
