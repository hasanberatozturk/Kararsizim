from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class RegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Parola"
        self.fields["password2"].label = "Parola (tekrar)"
        self.fields["username"].widget.attrs.update(autocomplete="username")
        self.fields["email"].widget.attrs.update(autocomplete="email")
        self.fields["email"].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu e-posta adresiyle zaten bir hesap var.")
        return email


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="E-posta",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Parola",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    error_messages = {
        "invalid_login": "E-posta veya parola hatalı.",
        "inactive": "E-posta veya parola hatalı.",
    }
