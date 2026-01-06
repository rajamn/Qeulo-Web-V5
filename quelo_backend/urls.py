"""
URL configuration for quelo_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from core.views import CustomLoginView, logout_view
from django.shortcuts import redirect
from django.http import HttpResponse
from django.views.generic import RedirectView
from django.templatetags.static import static
from queue_mgt.views import queue_display
from core.views import health_check,RootRedirectView
from hospital_portal.views import doctor_info_api


def health(_request): return HttpResponse("ok",status=200) #, content_type="text/plain")

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url=static("core/branding/favicon.ico"), permanent=False)),
    path("health/", health_check),
    re_path(r"^$", RootRedirectView.as_view(), name="root"),
    path("admin/", admin.site.urls),
    path('patients/', include(('patients.urls', 'patients'), namespace='patients')),
    path("doctors/", include(("doctors.urls", "doctors"), namespace="doctors")),
    path("queue/", include("queue_mgt.urls")),
    path("prescription/",include(("prescription.urls", "prescription"), namespace="prescription"),
),

    path("drugs/", include("drugs.urls")),
    path("reports/", include("reports.urls", namespace="reports")),
    path("billing/", include(("billing.urls", "billing"), namespace="billing")),
    path("display/", queue_display, name="queue_display"),
    path("vitals/", include("vitals.urls")),
    path("visit/", include(('visit_workspace.urls', 'visit_workspace'), namespace='visit_workspace')),

    
    path("whatsapp/", include("whatsapp_notifications.urls", namespace="whatsapp_notifications")),
    path("hospital-admin/", include("hospital_admin.urls")),
    path("api/doctor_info/<int:doctor_id>/", doctor_info_api, name="doctor_info_api_global"),
    path('h/', include('hospital_portal.urls')),

    # Keep auth-facing urls last; must include a route named "login"
    path("", include("core.urls")),

]


