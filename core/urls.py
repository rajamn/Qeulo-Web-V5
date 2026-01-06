from django.urls import path
from django.contrib.auth.views import LogoutView
from core.views import CustomLoginView,logout_view, doubletick_webhook
from core.views import change_password,profile
from django.shortcuts import redirect

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),  # ✅ Correct
    path('change-password/', change_password, name='change_password'),
    path('profile/', profile, name='profile'),
    path("webhooks/doubletick/", doubletick_webhook, name="doubletick_webhook"),
]
