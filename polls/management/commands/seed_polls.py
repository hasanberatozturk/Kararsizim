from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from polls.models import Option, Poll

SAMPLE_POLLS = [
    ("Bugün akşam yemeği ne olsun?", "", ["Pizza", "Kebap", "Makarna", "Ev yemeği", "Sushi"]),
    ("Bugün sinemaya mı gitsem, restorana mı?", "", ["Sinema", "Restoran", "Evde film"]),
    ("Sabah kahvesi ne olsun?", "", ["Türk kahvesi", "Filtre kahve", "Latte", "Çay"]),
    ("Bu akşam hangi diziyi izleyeyim?", "", ["Yeni bir dizi başlat", "Eski favorimi tekrar izle", "Film izle"]),
    ("Hafta sonu ne yapalım?", "", ["Doğa yürüyüşü", "Arkadaşlarla buluşma", "Evde dinlenme", "Alışveriş"]),
    ("Tatilde nereye gidelim?", "Fikir verin lütfen!", ["Kapadokya", "Ege kıyıları", "Karadeniz yaylaları", "Akdeniz"]),
    ("Yeni telefon alacağım, hangisi?", "Bütçem yaklaşık 20 bin TL.", ["iPhone", "Samsung", "Xiaomi", "Google Pixel"]),
    ("Python mu, JavaScript mi öğreneyim?", "", ["Python", "JavaScript", "İkisi birden"]),
    (
        "Yeni bir dil öğrenmeye karar verdim, hangisi?",
        "",
        ["İspanyolca", "Almanca", "Japonca", "Fransızca", "Arapça"],
    ),
    (
        "Yeni yıl hedefi ne olsun?",
        "",
        ["Spor yapmak", "Kitap okumak", "Yeni bir beceri öğrenmek", "Para biriktirmek"],
    ),
    ("Ananaslı pizza?", "", ["Evet, çok yakışıyor", "Hayır, kesinlikle olmaz"]),
    (
        "Sabah insanı mısın, gece kuşu mu?",
        "",
        ["Sabah insanı", "Gece kuşu", "İkisi de değil, hep uykuluyum"],
    ),
]


class Command(BaseCommand):
    help = "Örnek anketleri ekler. Aynı soruya sahip anket varsa atlar, bu yüzden tekrar çalıştırmak güvenlidir."

    def add_arguments(self, parser):
        parser.add_argument("--username", help="Anketlerin yazarı. Verilmezse ilk süper kullanıcı kullanılır.")

    def handle(self, *args, **options):
        User = get_user_model()
        if options["username"]:
            author = User.objects.filter(username__iexact=options["username"]).first()
        else:
            author = User.objects.filter(is_superuser=True).order_by("pk").first()
        if author is None:
            raise CommandError("Yazar bulunamadı. --username ile bir kullanıcı adı ver ya da önce createsuperuser çalıştır.")

        created = 0
        with transaction.atomic():
            for question, description, options_text in SAMPLE_POLLS:
                if Poll.objects.filter(author=author, question=question).exists():
                    continue
                poll = Poll.objects.create(author=author, question=question, description=description)
                Option.objects.bulk_create(
                    Option(poll=poll, text=text, order=index) for index, text in enumerate(options_text)
                )
                created += 1
        self.stdout.write(self.style.SUCCESS(f"@{author.username} için {created} anket eklendi, {len(SAMPLE_POLLS) - created} atlandı."))
