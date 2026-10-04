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
3. *Environment Variables* bölümüne ekle (deploy'dan **önce**, çünkü Vercel build sırasında ayarları yükler):
   `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL` (transaction pooler),
   `CSRF_TRUSTED_ORIGINS`.
4. Deploy et. Kontrol: `DJANGO_DEBUG=False python manage.py check --deploy`.

Vercel kalıcı disk sunmaz; production'da SQLite kullanılmaz.

## Bilinen prototip sınırları

- Üyesiz oy, imzalı çereze bağlıdır; çerezi silen biri tekrar oy verebilir.
- Oy değiştirme, anket kapatma, arama, yorum, parola sıfırlama henüz yok.
