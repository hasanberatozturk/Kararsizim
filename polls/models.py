from django.conf import settings
from django.core.validators import MaxValueValidator, MinLengthValidator
from django.db import models
from django.urls import reverse

MIN_OPTIONS = 2
MAX_OPTIONS = 5


class Poll(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="polls",
        verbose_name="yazar",
    )
    question = models.CharField("soru", max_length=200, validators=[MinLengthValidator(5)])
    description = models.TextField("açıklama", max_length=500, blank=True)
    created_at = models.DateTimeField("oluşturulma", auto_now_add=True)
    is_active = models.BooleanField("aktif", default=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "anket"
        verbose_name_plural = "anketler"

    def __str__(self):
        return self.question

    def get_absolute_url(self):
        return reverse("polls:detail", args=[self.pk])


class Option(models.Model):
    poll = models.ForeignKey(
        Poll, on_delete=models.CASCADE, related_name="options", verbose_name="anket"
    )
    text = models.CharField("seçenek", max_length=100)
    order = models.PositiveSmallIntegerField(
        "sıra", default=0, validators=[MaxValueValidator(MAX_OPTIONS - 1)]
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "seçenek"
        verbose_name_plural = "seçenekler"

    def __str__(self):
        return self.text


class Vote(models.Model):
    poll = models.ForeignKey(
        Poll, on_delete=models.CASCADE, related_name="votes", verbose_name="anket"
    )
    option = models.ForeignKey(
        Option, on_delete=models.CASCADE, related_name="votes", verbose_name="seçenek"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="votes",
        verbose_name="kullanıcı",
    )
    voter_key = models.CharField("oy veren anahtarı", max_length=64)
    created_at = models.DateTimeField("oluşturulma", auto_now_add=True)

    class Meta:
        verbose_name = "oy"
        verbose_name_plural = "oylar"
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "voter_key"],
                name="polls_vote_one_per_voter",
                violation_error_message="Bu ankete zaten oy verdin.",
            ),
        ]

    def __str__(self):
        return f"{self.voter_key} → {self.option}"
