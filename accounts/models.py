from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.db.models.functions import Lower

username_validator = RegexValidator(
    regex=r"^[A-Za-z0-9_.]+$",
    message="Kullanıcı adı yalnızca harf (a-z), rakam, alt çizgi (_) ve nokta (.) içerebilir.",
)


class UserManager(DjangoUserManager):
    def get_by_natural_key(self, email):
        # Emails are stored lowercased, so login is case-insensitive.
        return self.get(email=(email or "").strip().lower())


class User(AbstractUser):
    username = models.CharField(
        "kullanıcı adı",
        max_length=30,
        unique=True,
        validators=[MinLengthValidator(3), username_validator],
        help_text="3–30 karakter. Harf, rakam, _ ve . kullanılabilir.",
        error_messages={"unique": "Bu kullanıcı adı zaten alınmış."},
    )
    email = models.EmailField(
        "e-posta",
        unique=True,
        error_messages={"unique": "Bu e-posta adresiyle zaten bir hesap var."},
    )

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        verbose_name = "kullanıcı"
        verbose_name_plural = "kullanıcılar"
        constraints = [
            models.UniqueConstraint(
                Lower("username"),
                name="accounts_user_username_ci_unique",
                violation_error_message="Bu kullanıcı adı zaten alınmış.",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"@{self.username}"
