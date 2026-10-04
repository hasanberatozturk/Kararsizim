from django import forms

from .models import MAX_OPTIONS, MIN_OPTIONS, Option, Poll

OPTION_MAX_LENGTH = Option._meta.get_field("text").max_length


class PollForm(forms.ModelForm):
    """Poll question/description plus the repeated ``options`` inputs.

    Options are read straight from ``data.getlist("options")`` and validated
    on the server (2–5, non-empty, unique ignoring case).
    """

    class Meta:
        model = Poll
        fields = ("question", "description")
        widgets = {
            "question": forms.TextInput(attrs={"placeholder": "Bugün sinemaya mı gitsem, restorana mı?"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "İstersen kısa bir açıklama ekle"}),
        }

    def clean_question(self):
        return self.cleaned_data["question"].strip()

    def clean(self):
        cleaned = super().clean()
        raw = [text.strip() for text in self.data.getlist("options")]
        options = [text for text in raw if text]

        error = None
        if len(options) < MIN_OPTIONS:
            error = f"En az {MIN_OPTIONS} seçenek girmelisin."
        elif len(options) > MAX_OPTIONS:
            error = f"En fazla {MAX_OPTIONS} seçenek girebilirsin."
        elif any(len(text) > OPTION_MAX_LENGTH for text in options):
            error = f"Her seçenek en fazla {OPTION_MAX_LENGTH} karakter olabilir."
        elif len({text.casefold() for text in options}) != len(options):
            error = "Aynı seçeneği birden fazla kez giremezsin."

        if error:
            self.add_error(None, error)
        self.option_texts = options
        return cleaned

    def save(self, author):
        poll = super().save(commit=False)
        poll.author = author
        poll.save()
        Option.objects.bulk_create(
            Option(poll=poll, text=text, order=index) for index, text in enumerate(self.option_texts)
        )
        return poll
