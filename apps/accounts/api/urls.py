from django.urls import re_path

from .views import LoginView, LogoutView, MeView

urlpatterns = [
    re_path(r"^auth/login/?$", LoginView.as_view(), name="auth-login"),
    re_path(r"^auth/logout/?$", LogoutView.as_view(), name="auth-logout"),
    re_path(r"^me/?$", MeView.as_view(), name="me"),
]