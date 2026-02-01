from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from .forms import LoginForm
from django.urls import reverse_lazy
from django.contrib import messages
from core.forms import HospitalUserLoginForm
from django.views import View
from .forms import ProfileForm
from django.http import HttpResponse
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import login
from core.models import Hospital
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import date
from django.urls import reverse
from appointments.models import AppointmentDetails
from prescription.models import PrescriptionDraft




class CustomLoginView(LoginView):
    template_name = "core/login.html"
    authentication_form = HospitalUserLoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        """Authenticate user and redirect to internal queue."""
        user = form.get_user()
        login(self.request, user)

        # 🔒 Enforce password change if required
        if getattr(user, "must_change_password", False):
            return redirect("change_password")

        # ✅ Optional: set hospital_id in session for convenience (not required)
        hospital = getattr(user, "hospital", None)
        if hospital:
            self.request.session["hospital_id"] = hospital.id

        # ✅ Redirect all users to internal queue dashboard
        return redirect(self.get_success_url())

    # def get_success_url(self):
    #     """Redirect to main queue (no slug needed)."""
    #     return "/queue/"
    

    def get_success_url(self):
        user = self.request.user

        # Non-doctor users → Queue (unchanged behavior)
        if not user.doctor:
            return "/queue/"

        doctor = user.doctor
        today = date.today()

        # 1️⃣ RESUME ACTIVE DRAFT (not finalized)
        active_draft = (
            PrescriptionDraft.objects
            .filter(
                doctor=doctor,
                hospital=doctor.hospital,
                finalized=False,
                updated_at__date=date.today()
            )
            .order_by("-updated_at")
            .first()
        )


        if active_draft:
            return reverse(
                "prescription:ai_rx_review",
                args=[active_draft.id]
            )

        # 🔍 Find first IN-QUEUE patient for today
        next_appt = (
            AppointmentDetails.objects
            .filter(
                doctor=doctor,
                hospital=doctor.hospital,
                appointment_on=today,
                completed=AppointmentDetails.STATUS_IN_QUEUE
            )
            .order_by("que_pos")
            .first()
        )

        # 🚀 Auto-launch Doctor Workspace
        if next_appt:
            return (
                reverse("prescription:ai_rx_start")
                + f"?patient={next_appt.patient.id}&ai_mode=true&source=login"
            )

        # 🧭 No waiting patients → Doctor Dashboard
        return reverse("prescription:dw_entry")





@login_required
def change_password(request, slug=None):
    """
    Allows users to change their password.
    Works for both global (/change_password/) and slugged (/h/<slug>/change_password/) routes.
    """
    hospital = None
    if slug:
        hospital = get_object_or_404(Hospital, slug=slug)

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password and new_password == confirm_password:
            user = request.user
            user.set_password(new_password)
            user.must_change_password = False
            user.save()

            logout(request)  # ✅ safely log out
            messages.success(request, "✅ Password changed successfully. Please log in again.")

            # Redirect to appropriate login page
            if hospital:
                return redirect("hospital_login", slug=hospital.slug)
            return redirect("login")

        else:
            messages.error(request, "❌ Passwords do not match. Please try again.")

    return render(request, "change_password.html", {"hospital": hospital})


def logout_view(request, slug=None):
    """
    Logs out the current user.
    Works for both global and slugged logout routes.
    """
    hospital = None
    if slug:
        hospital = get_object_or_404(Hospital, slug=slug)

    logout(request)

    if hospital:
        return redirect("hospital_login", slug=hospital.slug)
    return redirect("login")



@login_required
def profile(request):
    # Bind the form directly to the user instance
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)

    return render(request, 'core/profile.html', {
        'form': form
    })

# in views.py


def health_check(request):
    return HttpResponse("OK", status=200)


class RootRedirectView(View):
    def get(self, request, *args, **kwargs):
        # Always redirect to global login
        return redirect("login")

# core/views.py

logger = logging.getLogger(__name__)

@csrf_exempt
def doubletick_webhook(request):
    if request.method == "POST":
        try:
            payload = json.loads(request.body.decode("utf-8"))
            logger.info("DoubleTick Webhook: %s", payload)
            print("🔥 Webhook received:", payload)  # also shows up in runserver console
            return JsonResponse({"status": "ok"})
        except Exception as e:
            logger.error("Webhook error: %s", e)
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"detail": "Method not allowed"}, status=405)
