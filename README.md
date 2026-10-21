# Kararsızım

Kararsız kaldığın konuları herkese sor, oylarla karar ver. Django + Supabase (yalnızca PostgreSQL) + Vercel.
Ayrıntılı proje planı: [docs/PLAN.md](docs/PLAN.md).

## Lokal kurulum

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`DATABASE_URL` boşsa SQLite (`db.sqlite3`) kullanılır. Testler: `python manage.py test`.

## Ortam değişkenleri

| Değişken | Açıklama |
|---|---|
| `DJANGO_SECRET_KEY` | Zorunlu (`DEBUG=False` iken). `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"` ile üret. |
| `DJANGO_DEBUG` | Lokalde `True`, production'da `False`. |
| `DJANGO_ALLOWED_HOSTS` | Virgülle ayrılmış. Örn. `localhost,127.0.0.1,.vercel.app` |
| `DATABASE_URL` | Boşsa SQLite. Production'da Supabase **transaction pooler** (port 6543). |
| `CSRF_TRUSTED_ORIGINS` | Örn. `https://*.vercel.app` |

`.env` dosyası asla commit edilmez.

## Veritabanı (Supabase)

Supabase yalnızca PostgreSQL olarak kullanılır; kimlik doğrulama Django'dadır.

1. Supabase'de proje oluştur. *Connect* menüsünden iki bağlantı dizesini al:
   - **Session pooler** (port 5432): migration için, lokalden.
   - **Transaction pooler** (port 6543): Vercel'deki uygulama için.
2. Migration (lokalden, session pooler ile):
   ```bash
   DATABASE_URL="<session-pooler-url>" python manage.py migrate
   ```
   PowerShell: `$env:DATABASE_URL="<session-pooler-url>"; python manage.py migrate`
3. Row Level Security: Django tabloları `public` şemasında oluşur ve Supabase bunu REST API ile açar.
   Her migration sonrası RLS'yi etkinleştir (politika eklenmez, anon anahtarı hiçbir tabloyu okuyamaz):
   ```bash
   DATABASE_URL="<session-pooler-url>" python manage.py enable_rls
   ```
4. Admin hesabı: `DATABASE_URL="<session-pooler-url>" python manage.py createsuperuser`

## Vercel'e yayınlama

1. Repoyu GitHub'a gönder.
2. Vercel'de *Add New → Project* ile repoyu içe aktar. Vercel `manage.py` dosyasından Django'yu algılar,
   `WSGI_APPLICATION` giriş noktasını kullanır ve `collectstatic`'i build sırasında kendisi çalıştırır.
   Python sürümü `.python-version` (3.12), fonksiyon bölgesi `vercel.json` (`fra1`, Supabase ile aynı bölge) ile belirlenir.
3. *Environment Variables* bölümüne ekle, hepsi yalnızca **Production** için. Bunları deploy'dan **önce**
   gir: Vercel build sırasında `manage.py` ile ayarları yükler, eksik `DJANGO_SECRET_KEY` build'i kırar.

   | Değişken | Değer |
   |---|---|
   | `DJANGO_SECRET_KEY` | Rastgele anahtar (Secret olarak kaydet) |
   | `DJANGO_DEBUG` | `False` |
   | `DJANGO_ALLOWED_HOSTS` | `.vercel.app` (özel alan adı eklenirse onu da) |
   | `CSRF_TRUSTED_ORIGINS` | `https://<proje-adi>.vercel.app` (joker `*` kullanma) |
   | `DATABASE_URL` | Transaction pooler (port **6543**) + `?sslmode=require` (Secret olarak kaydet) |

   `DJANGO_SECURE_SSL_REDIRECT` Vercel'de **ayarlanmaz** (varsayılan açık); yalnızca `DEBUG=False`'u lokalde
   denerken `False` yapılır.

   `DATABASE_URL` biçimi, tek satır ve tırnaksız:
   ```
   postgresql://postgres.<PROJE-REF>:<PAROLA>@<POOLER-HOST>:6543/postgres?sslmode=require
   ```
   Parolada köşeli parantez olmamalı; `@ # ? / : %` gibi karakterler URL kodlaması ister, en kolayı yalnızca
   harf ve rakamdan oluşan bir parola kullanmaktır. Biçim hatalıysa build log'unda parolayı göstermeden
   neyin yanlış olduğunu söyleyen bir `DATABASE_URL geçersiz ...` satırı çıkar.
4. Deploy et. Ortam değişkenlerini sonradan değiştirirsen eski dağıtımlara uygulanmaz; **Redeploy** gerekir.
5. Kontrol: `DJANGO_DEBUG=False python manage.py check --deploy` ve canlı adreste kayıt, giriş, anket
   oluşturma, oy verme ve `/admin/`.

Vercel kalıcı disk sunmaz; production'da SQLite kullanılmaz.

### Örnek anketler

Boş bir veritabanına 12 örnek anket ekler (ilk süper kullanıcıya ya da `--username` ile verilen kullanıcıya;
tekrar çalıştırmak güvenlidir):

```bash
DATABASE_URL="<session-pooler-url>" python manage.py seed_polls
```

### Production'ı lokalde denemek

`.env` içinde `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY=<anahtar>` ve `DJANGO_SECURE_SSL_REDIRECT=False` ayarla,
önce `python manage.py collectstatic --noinput` çalıştır, sonra `python manage.py runserver --noreload`.
`DEBUG=False` iken `DJANGO_SECRET_KEY` zorunludur.

## Bilinen prototip sınırları

- Üyesiz oy, imzalı çereze bağlıdır; çerezi silen ya da hiç göndermeyen biri tekrar oy verebilir ve oy
  gönderimine hız sınırı yoktur. Giriş, kayıt ve `/admin/` için de uygulama içi hız sınırı ve e-posta
  doğrulaması yoktur; yayında Vercel Firewall'da bu adreslere hız sınırı kuralı eklenmesi önerilir.
- Oy değiştirme, anket kapatma, arama, yorum, parola sıfırlama henüz yok.
