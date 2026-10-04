# Kararsızım — Proje Planı

> Bu dosya Claude Code için hazırlanmış ana yol haritasıdır. Her oturumda önce bu dosyayı oku, sonra yalnızca istenen fazı uygula. Bir fazı bitirdiğinde en alttaki **Durum** bölümünü güncelle.

---

## 1. Proje Özeti

**Kararsızım**, kullanıcıların kararsız kaldıkları konularda diğer kullanıcılara danışmak için anket açtığı bir web uygulamasıdır.

Örnek: *"Bugün sinemaya mı gitsem, restorana mı?"* → 2–5 seçenek → herkes oy verir → sonuçlar canlı çubuklarla görünür.

### Temel kurallar

| Kural | Açıklama |
|---|---|
| Takip yok | Takipçi/takip edilen mekanizması yoktur. Platformdaki **her anket herkese görünür**. |
| Üyesiz kullanım | Üye olmayan ziyaretçiler anketleri **görüntüleyebilir ve oy verebilir**. |
| Anket oluşturma | Yalnızca **üye** kullanıcılar anket oluşturabilir. |
| Seçenek sayısı | Her ankette **en az 2, en fazla 5** seçenek bulunur. |
| Kimlik | Kayıtta **e-posta + kullanıcı adı + parola** zorunludur. |
| Gizlilik | Anketlerde **yalnızca kullanıcı adı** görünür. E-posta hiçbir herkese açık sayfada asla gösterilmez. |
| Tek oy | Bir kişi bir ankette yalnızca **bir kez** oy verebilir (prototipte oy değiştirme yok). |

### Hedef
İlk hedef **çalışan bir prototip**. Gereksiz karmaşıklıktan kaçın: ek framework, SPA, REST framework, Celery, Redis vb. **kullanma**. Özellikler sonradan adım adım eklenecek.

---

## 2. Teknoloji Yığını

| Katman | Seçim | Not |
|---|---|---|
| Dil | Python 3.12+ | |
| Backend | Django 5.x | Django'nun yerleşik auth, form ve template sistemi kullanılacak |
| Veritabanı | Supabase (PostgreSQL) | **Yalnızca Postgres olarak** kullanılır. Supabase Auth / Storage / REST **kullanılmaz**; kimlik doğrulama Django'dadır. |
| Lokal geliştirme DB | SQLite | `DATABASE_URL` tanımlı değilse otomatik SQLite |
| Frontend | Django template + saf HTML / CSS / JavaScript | Aynı repo içinde, ayrı framework yok, build adımı yok |
| Deployment | Vercel | Vercel, `manage.py` dosyasını görerek Django projesini sıfır konfigürasyonla algılar |

### Python paketleri (minimum)
```
Django>=5.0,<6.0
psycopg[binary]
dj-database-url
python-dotenv
whitenoise        # statik dosyalar için yedek çözüm (Vercel CDN yeterliyse kaldırılabilir)
```

---

## 3. Klasör Yapısı

```
kararsizim/
├── manage.py
├── requirements.txt
├── pyproject.toml            # Vercel ayarları gerekirse buraya
├── .env.example
├── .gitignore
├── PLAN.md                   # bu dosya
├── config/                   # Django proje ayarları
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/                 # özel kullanıcı modeli, kayıt/giriş
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── tests.py
├── polls/                    # anket, seçenek, oy
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── utils.py              # voter_key üretimi vb.
│   └── tests.py
├── templates/
│   ├── base.html
│   ├── partials/
│   │   ├── navbar.html
│   │   ├── poll_card.html
│   │   └── messages.html
│   ├── accounts/
│   │   ├── register.html
│   │   └── login.html
│   └── polls/
│       ├── list.html
│       ├── detail.html
│       ├── create.html
│       └── user_polls.html
└── static/
    ├── css/
    │   └── main.css
    └── js/
        ├── main.js
        ├── poll_form.js      # dinamik seçenek ekle/çıkar
        └── vote.js           # fetch ile oy verme + sonuç animasyonu
```

**Kod dili:** Değişken, fonksiyon, model ve dosya adları **İngilizce**. Kullanıcıya görünen tüm metinler **Türkçe**.

---

## 4. Veri Modeli

> ⚠️ **Özel kullanıcı modeli ilk migration'dan ÖNCE tanımlanmalı.** Sonradan değiştirmek çok zahmetlidir.

### `accounts.User` (AbstractUser'dan türetilir)
| Alan | Tip | Kural |
|---|---|---|
| `email` | EmailField | `unique=True`, zorunlu, küçük harfe çevrilerek saklanır |
| `username` | CharField(30) | `unique=True`, zorunlu, 3–30 karakter, yalnızca harf/rakam/`_`/`.` |
| `password` | (Django) | Django'nun parola doğrulayıcıları açık |

- `USERNAME_FIELD = "email"` → giriş **e-posta + parola** ile yapılır.
- `REQUIRED_FIELDS = ["username"]`
- Kullanıcı adı karşılaştırması büyük/küçük harf duyarsız olmalı (`Ali` ve `ali` aynı kabul edilir).
- `settings.AUTH_USER_MODEL = "accounts.User"`

### `polls.Poll`
| Alan | Tip | Kural |
|---|---|---|
| `author` | FK → User | `on_delete=CASCADE`, `related_name="polls"` |
| `question` | CharField(200) | zorunlu, en az 5 karakter |
| `description` | TextField(500) | opsiyonel, kısa açıklama |
| `created_at` | DateTimeField | `auto_now_add` |
| `is_active` | BooleanField | varsayılan `True` (ileride anket kapatma için) |

- Varsayılan sıralama: `-created_at`
- Yardımcı: `total_votes` (annotate ile hesaplanır, alan olarak saklanmaz)

### `polls.Option`
| Alan | Tip | Kural |
|---|---|---|
| `poll` | FK → Poll | `CASCADE`, `related_name="options"` |
| `text` | CharField(100) | zorunlu |
| `order` | PositiveSmallIntegerField | 0–4, görüntüleme sırası ve renk eşlemesi için |

- Aynı ankette aynı metne sahip iki seçenek olamaz (formda kontrol, büyük/küçük harf duyarsız).

### `polls.Vote`
| Alan | Tip | Kural |
|---|---|---|
| `poll` | FK → Poll | `CASCADE`, `related_name="votes"` |
| `option` | FK → Option | `CASCADE`, `related_name="votes"` |
| `user` | FK → User | `null=True, blank=True`, `SET_NULL` (üyesiz oylar için boş) |
| `voter_key` | CharField(64) | oy verenin benzersiz anahtarı |
| `created_at` | DateTimeField | `auto_now_add` |

- **`UniqueConstraint(fields=["poll", "voter_key"])`** → aynı kişi aynı ankete iki kez oy veremez (veritabanı seviyesinde garanti).
- `option.poll == poll` olmalı (view'da doğrula).

### `voter_key` mantığı (`polls/utils.py`)
- **Üye kullanıcı:** `voter_key = f"u:{user.id}"`
- **Üyesiz ziyaretçi:** İlk ziyarette `uuid4` üretilir, **imzalı ve HttpOnly** bir çereze (`kararsizim_voter`, 1 yıl ömür, `SameSite=Lax`) yazılır. `voter_key = f"a:{uuid}"`.
- Django'nun `request.get_signed_cookie` / `response.set_signed_cookie` fonksiyonları kullanılır.
- Bilinen prototip sınırı: Çerezi silen veya gizli sekme kullanan biri tekrar oy verebilir. Bu prototip için kabul edilebilir; ileride IP hash + rate limit eklenebilir.

---

## 5. Sayfalar ve URL'ler

| URL | Sayfa | Erişim |
|---|---|---|
| `/` | Anket akışı (tüm anketler, en yeni üstte, sayfa başına 10) | Herkes |
| `/?sirala=populer` | En çok oy alanlar | Herkes |
| `/anket/<id>/` | Anket detayı + oy verme / sonuçlar | Herkes |
| `/anket/yeni/` | Anket oluşturma | **Yalnızca üye** (değilse girişe yönlendir, `?next=` ile geri dön) |
| `/anket/<id>/sil/` | Anketi sil (POST) | Yalnızca anketin sahibi |
| `/anket/<id>/oy/` | Oy ver (POST, JSON yanıt) | Herkes |
| `/u/<username>/` | Bir kullanıcının anketleri | Herkes (yalnızca kullanıcı adı görünür) |
| `/kayit/` | Kayıt | Misafir |
| `/giris/` | Giriş | Misafir |
| `/cikis/` | Çıkış (**POST**) | Üye |
| `/admin/` | Django admin | Süper kullanıcı |

### Davranış detayları
- **Anket kartı** şunları gösterir: soru, yazarın **kullanıcı adı** (`@ali` gibi, `/u/ali/`'ye link), göreli zaman ("3 saat önce" — `timesince`), seçenekler, toplam oy sayısı.
- **Oy vermeden önce:** seçenekler tıklanabilir renkli butonlar olarak görünür.
- **Oy verdikten sonra (veya daha önce oy verdiyse):** butonlar yerini yüzdelik sonuç çubuklarına bırakır, kişinin seçtiği seçenek ✓ ile işaretlenir.
- **Oylama listede de yapılabilir**, detay sayfasına gitmek zorunlu değil.
- Anket sahibi kendi anketine oy verebilir.
- Oy verme `fetch` ile yapılır, sayfa yenilenmez. JavaScript kapalıysa normal form POST'u çalışmaya devam eder (progressive enhancement).

### Oy endpoint'i (`POST /anket/<id>/oy/`)
İstek: `option_id` (form-encoded veya JSON), CSRF token zorunlu.

Başarılı yanıt (200):
```json
{
  "ok": true,
  "voted_option_id": 12,
  "total_votes": 37,
  "results": [
    {"id": 11, "text": "Sinema", "votes": 20, "percent": 54},
    {"id": 12, "text": "Restoran", "votes": 17, "percent": 46}
  ]
}
```
Hatalar: zaten oy verilmişse `409` + mevcut sonuçlar; geçersiz seçenekse `400`; anket pasifse `403`. Tüm hata mesajları Türkçe.

> Çift oy kontrolü için önce `exists()` sorgusuna güvenme; `IntegrityError` yakalayarak veritabanı kısıtını esas al (eş zamanlı isteklerde güvenli).

---

## 6. Formlar ve Doğrulama

### Kayıt formu
- Alanlar: kullanıcı adı, e-posta, parola, parola tekrar.
- E-posta ve kullanıcı adı benzersizliği (büyük/küçük harf duyarsız) kontrol edilir.
- Hatalar Türkçe ve alanın hemen altında gösterilir.
- Başarılı kayıttan sonra kullanıcı otomatik giriş yapar ve ana sayfaya yönlendirilir.

### Giriş formu
- E-posta + parola. Hatalı girişte genel bir mesaj: *"E-posta veya parola hatalı."* (hangisinin yanlış olduğunu söyleme).

### Anket oluşturma formu
- Soru (zorunlu), açıklama (opsiyonel).
- Seçenekler: sayfa **2 boş seçenek alanıyla** açılır.
  - "＋ Seçenek ekle" butonu (5'e ulaşınca devre dışı kalır).
  - Her seçeneğin yanında "✕" butonu (2'nin altına inilemez).
  - Seçenek sayısı göstergesi: "3 / 5".
- **Sunucu tarafında da** kontrol edilir: boş olmayan, benzersiz 2–5 seçenek. İstemci tarafı kontrol yalnızca kolaylık içindir.
- Basit tutmak için seçenekler `options` adında tekrarlanan input'larla gönderilir ve `request.POST.getlist("options")` ile alınır (formset kullanmak zorunlu değil).
- Kaydetme işlemi `transaction.atomic()` içinde yapılır.

---

## 7. Arayüz ve Tasarım

### Genel his
Modern, canlı, enerjik ve eğlenceli; ama okunaklı ve sade. Mobil öncelikli (mobile-first). Karar vermenin "hafif ve keyifli" bir şey olduğu hissi verilmeli.

### Renk paleti (CSS değişkenleri olarak `:root` içinde)
```css
--color-primary:   #7C3AED;  /* canlı mor */
--color-secondary: #EC4899;  /* pembe */
--color-accent:    #F97316;  /* turuncu */
--color-success:   #10B981;  /* yeşil */
--color-info:      #06B6D4;  /* camgöbeği */
--color-warning:   #FACC15;  /* sarı */

--color-bg:        #FAF7FF;  /* çok açık mor-beyaz */
--color-surface:   #FFFFFF;
--color-text:      #1E1B2E;
--color-muted:     #6B6880;
--color-border:    #ECE6F7;

--gradient-hero: linear-gradient(135deg, #7C3AED 0%, #EC4899 55%, #F97316 100%);
```

### Seçenek renkleri
En fazla 5 seçenek olduğu için her `order` değerine sabit bir renk atanır:
`0 → mor`, `1 → pembe`, `2 → turuncu`, `3 → camgöbeği`, `4 → yeşil`. Butonlar ve sonuç çubukları bu renkleri kullanır.

### Tipografi
- Google Fonts: **"Plus Jakarta Sans"** (400, 600, 800).
- Başlıklar kalın (800), soru metinleri büyük ve net.

### Bileşenler
- **Navbar:** Sol tarafta gradyan yazılı "Kararsızım" logosu; sağda "Anket Oluştur" (gradyan buton), giriş/kayıt veya `@kullaniciadi` + çıkış.
- **Hero (ana sayfa üstü, kısa):** "Kararsız mı kaldın? Bir sor, herkes oylasın." + oluştur butonu.
- **Anket kartı:** beyaz yüzey, `border-radius: 20px`, yumuşak gölge, hover'da hafif yükselme.
- **Seçenek butonları:** tam genişlik, yuvarlatılmış, seçenek rengiyle ince kenarlık; hover'da dolgu.
- **Sonuç çubukları:** genişlik `0%`'dan gerçek yüzdeye `transition` ile animasyonlu dolar; yüzde ve oy sayısı sağda.
- **Bildirimler:** Django messages → sağ üstte kaybolan "toast".
- **Boş durum:** henüz anket yoksa eğlenceli bir mesaj + oluştur butonu.

### Kurallar
- CSS framework (Bootstrap, Tailwind) **kullanma**; tek bir `main.css` yeterli.
- Responsive: 640px altı tek sütun; masaüstünde içerik genişliği en fazla ~720px, ortalı.
- Erişilebilirlik: yeterli kontrast, `:focus-visible` stilleri, buton ve inputlarda etiketler.
- Animasyonlar kısa (150–400ms); `prefers-reduced-motion` desteklenir.

---

## 8. Ortam Değişkenleri

`.env.example`:
```
DJANGO_SECRET_KEY=degistir-beni
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,.vercel.app
DATABASE_URL=                # boşsa SQLite kullanılır
CSRF_TRUSTED_ORIGINS=https://*.vercel.app
```

- `.env` dosyası **asla** commit edilmez (`.gitignore`'a ekle).
- `settings.py` değerleri `os.environ` / `python-dotenv` üzerinden okur.
- `DEBUG=False` iken: `SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` açık olmalı.
- `LANGUAGE_CODE = "tr"`, `TIME_ZONE = "Europe/Istanbul"`, `USE_TZ = True`.

---

## 9. Supabase ve Vercel Notları

### Supabase bağlantısı
- Uygulama (Vercel, sunucusuz) için **Transaction pooler** bağlantı dizesini kullan (port **6543**). Sunucusuz ortamlar için önerilen mod budur.
- Transaction modunda prepared statement desteklenmez ve sunucu tarafı cursor'lar çalışmaz. Bu yüzden Django ayarlarında:
  ```python
  DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
  DATABASES["default"]["CONN_MAX_AGE"] = 0
  ```
- **Migration'ları** lokal bilgisayardan, **Session pooler** (port 5432) bağlantı dizesiyle çalıştır:
  ```bash
  DATABASE_URL="<session-pooler-url>" python manage.py migrate
  ```
- 🔐 **Güvenlik (önemli):** Django tabloları Supabase'in `public` şemasında oluşur ve Supabase bu şemayı varsayılan olarak REST (Data) API ile dışarı açar. Supabase'in anon anahtarıyla tablolara erişilmesini engellemek için migration'dan sonra **tüm tablolarda RLS'yi etkinleştir** (politika ekleme). Django `postgres` rolüyle bağlandığı için RLS'den etkilenmez. Alternatif: Supabase panelinden Data API'yi kapat.
  ```sql
  -- public şemasındaki tüm tablolar için
  DO $$ DECLARE r record; BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
      EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', r.tablename);
    END LOOP;
  END $$;
  ```
  Bu komut her yeni tablo oluşturan migration'dan sonra tekrar çalıştırılmalı (veya ileride bir Django management command'a dönüştürülebilir).

### Vercel
- Vercel, kökteki `manage.py` dosyasından Django projesini otomatik algılar; `vercel.json` ile yönlendirme veya `/api` klasörü gerekmez.
- Statik dosyalar Vercel CDN'den sunulur. `STATIC_ROOT` tanımlı olmalı; `collectstatic` build sırasında çalışmalı. Kurulum sırasında **Vercel'in güncel Django dokümantasyonunu kontrol et** (https://vercel.com/docs/frameworks/full-stack/django) ve gerekirse `pyproject.toml` içinde `[tool.vercel]` ayarlarını kullan.
- Vercel ortam değişkenlerine `.env.example`'daki tüm anahtarları ekle (`DJANGO_DEBUG=False`, `DATABASE_URL` = transaction pooler).
- Vercel fonksiyonları kalıcı disk sunmaz: SQLite production'da **kullanılmaz**, kullanıcı dosya yüklemesi prototipte yok.

---

## 10. Fazlar

Her faz kendi içinde çalışır durumda bitmeli. Bir fazı bitirmeden sonrakine geçme.

### Faz 1 — Proje iskeleti ve veri modeli
**Yapılacaklar**
- Django projesini (`config`) ve `accounts`, `polls` uygulamalarını oluştur.
- `requirements.txt`, `.env.example`, `.gitignore` dosyalarını ekle.
- `settings.py`: ortam değişkenleri, `dj-database-url` (yoksa SQLite), Türkçe dil/saat dilimi, `templates/` ve `static/` klasörleri.
- **Özel `User` modelini** (bölüm 4) yaz ve `AUTH_USER_MODEL`'i ayarla — ilk `migrate`'ten önce.
- `Poll`, `Option`, `Vote` modellerini ve kısıtlarını yaz.
- Admin'e modelleri kaydet (Poll admin'inde Option'lar inline).
- `base.html` iskeleti ve basit bir ana sayfa ("Kararsızım çalışıyor").

**Kabul kriterleri**
- `python manage.py migrate` hatasız çalışıyor, `runserver` ile ana sayfa açılıyor.
- Admin'den anket + seçenek eklenebiliyor.
- Aynı `poll` + `voter_key` ile ikinci oy veritabanı tarafından reddediliyor (test ile).

---

### Faz 2 — Kimlik doğrulama
**Yapılacaklar**
- Kayıt (`/kayit/`), giriş (`/giris/`), çıkış (`/cikis/`, POST) sayfaları ve formları (bölüm 6).
- E-posta ile giriş (özel model `USERNAME_FIELD="email"` sayesinde Django'nun `LoginView`'ı kullanılabilir).
- Navbar'da giriş durumuna göre linkler.
- `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL` ayarları.

**Kabul kriterleri**
- Kayıt → otomatik giriş → navbar'da `@kullaniciadi` görünüyor.
- Aynı e-posta veya kullanıcı adıyla (büyük/küçük harf farklı olsa da) ikinci kayıt reddediliyor.
- Hiçbir sayfada e-posta adresi görünmüyor.
- Testler: kayıt, giriş, benzersizlik.

---

### Faz 3 — Anket oluşturma ve listeleme
**Yapılacaklar**
- `/anket/yeni/` sayfası ve `poll_form.js` ile dinamik seçenek ekle/çıkar (2–5).
- Sunucu tarafı doğrulama (bölüm 6), `transaction.atomic()` ile kaydetme.
- `/` ana sayfada tüm anketlerin listesi (sayfalama: 10), `?sirala=populer` seçeneği.
- `/anket/<id>/` detay sayfası.
- `/u/<username>/` kullanıcının anketleri.
- Anket sahibinin kendi anketini silebilmesi (onay penceresiyle, POST).
- N+1 sorgularından kaçın: `select_related("author")`, `prefetch_related("options")`, `annotate(total_votes=Count("votes"))`.

**Kabul kriterleri**
- Üye olmayan kullanıcı `/anket/yeni/`'ye gidince giriş sayfasına yönlendiriliyor, girişten sonra forma geri dönüyor.
- 1 veya 6 seçenekli anket sunucu tarafından reddediliyor.
- Anket kartında e-posta değil kullanıcı adı görünüyor.
- Başkasının anketini silmeye çalışmak 403/404 döndürüyor.
- Testler: yetki, seçenek sınırları, silme yetkisi.

---

### Faz 4 — Oylama
**Yapılacaklar**
- `polls/utils.py`: `get_voter_key(request)` ve anonim çerez yönetimi (bölüm 4).
- `/anket/<id>/oy/` endpoint'i (bölüm 5'teki JSON sözleşmesi).
- `vote.js`: seçeneğe tıklanınca `fetch` ile POST (CSRF token header'da), yanıtla butonları animasyonlu sonuç çubuklarına çevir.
- Sayfa yüklenirken kullanıcının daha önce oy verdiği anketlerde doğrudan sonuçları göster (listede tek sorguyla: kullanıcının `voter_key`'ine ait oyları önceden çek).
- JavaScript yoksa normal form POST'u ile çalışan yedek akış.

**Kabul kriterleri**
- Üye olmayan ziyaretçi oy verebiliyor; sayfayı yenilediğinde sonuçları görüyor ve tekrar oy veremiyor.
- Üye kullanıcı farklı tarayıcıdan giriş yapsa da aynı ankete ikinci kez oy veremiyor.
- Başka bir ankete ait `option_id` ile oy verme reddediliyor.
- Yüzdeler toplamı ~100 (yuvarlama farkı kabul edilebilir).
- Testler: anonim oy, üye oyu, çift oy, yanlış seçenek, CSRF.

---

### Faz 5 — Arayüz cilası
**Yapılacaklar**
- Bölüm 7'deki tasarım sistemini eksiksiz uygula: renkler, gradyanlar, tipografi, kartlar, seçenek renkleri, toast bildirimleri, boş durumlar.
- Mobil, tablet ve masaüstü kırılımlarını kontrol et.
- Form hatalarının şık gösterimi, buton yükleniyor durumları (oy gönderilirken).
- Favicon (basit, emoji tabanlı SVG olabilir: 🤔) ve sayfa başlıkları / meta açıklamaları.
- 404 ve 500 için özel, temaya uygun hata sayfaları.

**Kabul kriterleri**
- 375px genişlikte yatay kaydırma yok, tüm butonlar rahat tıklanabiliyor.
- Klavye ile tüm akış (kayıt, anket oluşturma, oy verme) yapılabiliyor.
- Sonuç çubukları animasyonlu doluyor; `prefers-reduced-motion` açıkken animasyon yok.

---

### Faz 6 — Supabase + Vercel ile yayına alma
**Yapılacaklar**
- Supabase projesi oluştur, transaction (6543) ve session (5432) pooler bağlantı dizelerini al.
- Session pooler ile lokalden `migrate` çalıştır, ardından RLS komutunu uygula (bölüm 9).
- `createsuperuser` ile admin hesabı oluştur.
- Production ayarlarını tamamla (`DEBUG=False`, güvenli çerezler, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `STATIC_ROOT`).
- Repoyu GitHub'a gönder, Vercel'e bağla, ortam değişkenlerini gir, deploy et.
- `README.md`: lokal kurulum, ortam değişkenleri, migration ve deploy adımları.

**Kabul kriterleri**
- `*.vercel.app` adresinde kayıt, giriş, anket oluşturma ve oy verme çalışıyor.
- CSS/JS dosyaları production'da yükleniyor.
- Supabase anon anahtarıyla REST API üzerinden tablolar okunamıyor.
- `python manage.py check --deploy` kritik uyarı vermiyor.

---

### Sonraki adımlar (prototip sonrası, şimdilik YAPMA)
- Oy değiştirme / geri çekme
- Anket bitiş süresi ve "kapanmış" anketler
- Arama ve kategori/etiketler
- Yorumlar
- Paylaşım linki + Open Graph görselleri
- IP tabanlı rate limit ve bot koruması
- Karanlık mod
- Parola sıfırlama (e-posta gönderimi)

---

## 11. Claude Code için Çalışma Kuralları

1. Her fazın başında bu dosyayı oku; yalnızca istenen fazı uygula, kapsam dışına çıkma.
2. Bölüm 2'de olmayan bir paket eklemek gerekirse önce gerekçesiyle sor.
3. Her fazda en az kabul kriterlerini kapsayan Django testleri yaz ve `python manage.py test` ile çalıştır.
4. Faz sonunda: değişikliklerin kısa özetini ver, manuel test adımlarını listele ve aşağıdaki **Durum** bölümünü güncelle.
5. Gizli bilgileri (secret key, veritabanı parolası) asla koda veya commit'e yazma.
6. Kullanıcıya görünen metinler Türkçe, kod İngilizce.
7. Basit olanı seç: prototip için okunabilirlik > soyutlama.

---

## 12. Durum

- [x] Faz 1 — Proje iskeleti ve veri modeli
- [x] Faz 2 — Kimlik doğrulama
- [x] Faz 3 — Anket oluşturma ve listeleme
- [x] Faz 4 — Oylama
- [x] Faz 5 — Arayüz cilası
- [ ] Faz 6 — Supabase + Vercel ile yayına alma

---

## Ek: Fazları başlatmak için hazır promptlar

Claude Code'a fazları tek tek şu şekilde verebilirsin:

**Faz 1:**
> `PLAN.md` dosyasını baştan sona oku. Sadece **Faz 1**'i uygula. Özel kullanıcı modelini ilk migration'dan önce tanımla. Bitince testleri çalıştır, kabul kriterlerini tek tek doğrula ve Durum bölümünü güncelle.

**Faz 2–5:**
> `PLAN.md` dosyasını oku ve mevcut kodu incele. Sadece **Faz N**'i uygula, önceki fazların davranışını bozma. Bitince testleri çalıştır, kabul kriterlerini doğrula ve Durum bölümünü güncelle.

**Faz 6:**
> `PLAN.md` dosyasındaki **Faz 6**'yı uygula. Supabase ve Vercel panelinde benim yapmam gereken adımları ayrı bir liste olarak ver; kod tarafındaki production ayarlarını ve README'yi sen hazırla.
