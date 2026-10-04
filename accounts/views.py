from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.views.generic import CreateView

from .forms import EmailLoginForm, RegisterForm


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("polls:list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, f"Hoş geldin, @{user.username}!")
        return redirect("polls:list")


class UserLoginView(LoginView):
    form_class = EmailLoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    """Logout is POST-only (Django 5)."""
