# MASTERWORLD — canlı veri küresi (masterworld.app)

Kamuya açık canlı veri kaynaklarını (uçak, gemi, uydu, deprem, kamera, radyo …) tam ekran 3B küreye yerleştiren web uygulaması.
Üyelik **isteğe bağlı** (mastertool.download hesabı); üye olmayanın ayarları tarayıcıda, üyeninki hesap servisinde saklanır.
Bu belge hesap servisi / Merkez / masterworld sunucusu arasındaki sözleşmedir; değişiklik yapan bu dosyayı da günceller.

## 1. Mimari

- **Harita:** MapLibre GL JS **6.15.0** (5.x'in devamı; küre projeksiyonu), sürüm sabit ve **yerel** (`static/vendor/maplibre-gl/`; ES modülü + worker aynı kökenden — CDN yok).
  Altlık: OpenFreeMap vektör stil (anahtarsız) + NASA GIBS raster (uydu / gece ışıkları; kamu malı). Altlıklar "veri kaynağı" sayılmaz,
  istemci doğrudan yükler. Cesium KULLANILMAZ (kullanıcı kararı 2026-10-20).
- **masterworld sunucusu:** ayrı depo `goktalay/masterworld` (bağımsız FastAPI uygulaması `app.main:app` + `static/`). PROD:
  `/opt/hepgo/masterworld` (root:root), veri `/opt/hepgo/masterworld-data`, systemd `hepgo-masterworld` (User=hepgo, UDS
  `/run/hepgo/masterworld.sock`), cloudflared ingress `masterworld.app` + `www.masterworld.app`. Yayın SIMUMAV kalıbı (§6).
- **Kaynak kaydı:** mastertool.download hesap servisi veritabanı (`central/sshmaster_server`, `data/sshm.db`) `mw_sources` + `mw_points`.
  Yönetim Merkez › Mastertool › **MASTERWORLD** sekmesinden (Merkez → hesap servisi iç anahtarla, mevcut `_sm` vekil kalıbı).
  masterworld sunucusu kaydı hesap servisinin iç ucundan 60 sn'de bir çeker (§3.3), son başarılı kopyayı diske yazar (hesap servisi
  düşerse son bilinenle çalışır).
- **Kimlik:** hesap servisi uygulama kodu **`mw`** (`GAMES['mw']`, `site` = https://masterworld.app). Tarayıcı mastertool.download'a
  doğrudan giriş yapar (`/api/mw/auth/prelogin|login|register|forgot…`, Bearer; `credentials:'omit'`; CORS yalnız masterworld.app
  kökeni ve yalnız `/api/mw/*`). Ayarlar `GET/PUT /api/mw/profile` (Bearer) → `mw_profiles`. masterworld sunucusu kullanıcı kimliği
  TUTMAZ (oturum/çerez yok); tüm veri uçları anonimdir.

## 2. Kaynak türleri

`category` (kategori, Excel "Kategori"den eşlenir) ve `kind` (katman türü: simge, renk, tıklama davranışı):

| category | Excel | kind örnekleri |
|---|---|---|
| `air` | Hava trafiği | aircraft |
| `sea` | Deniz trafiği | vessel, warning |
| `space` | Uzay | satellite, iss, aurora |
| `natural` | Doğal olaylar | quake, fire, disaster, event, volcano, lightning |
| `weather` | Meteoroloji | metar, buoy, sonde, radar (karo), forecast (tıklanan nokta), alert |
| `environment` | Çevre | airquality, radiation, imagery |
| `camera` | Kamera | camera → **tıklayınca küçük canlı önizleme** (görüntü, N sn'de bir yenilenir) |
| `radio` | (yeni) | radio → **mini dinleme paneli** (ses akışı) |
| `ground` | Kara ulaşımı | transit, bike |
| `basemap` | Altlık | basemap (katalog) |
| `ham` | Telsiz | aprs, spot |
| `infra` | Altyapı | cable (çizgi), plant, cell, internet |
| `news` | Olay / Haber | news |

Excel'de olmayan, eklenen kaynaklar (`origin='builtin'`, `sshm/mw_catalog.py` `BUILTIN`; üçü de etkin ve varsayılan görünür):
**Radio Browser** (`radio-browser`, adaptör `radio_browser`; radio; anahtarsız, kamu), **Caltrans CCTV** (`caltrans-cctv`, `caltrans_cctv`; camera;
anahtarsız, ABD Kaliforniya DOT trafik kameraları — "ABD eyalet 511 / DOT" satırının somut örneği), **Digitraffic Weathercams (Finlandiya)**
(`digitraffic-cam`, `digitraffic_cam`; camera; anahtarsız, CC BY 4.0, atıf zorunlu: "Fintraffic / digitraffic.fi (CC BY 4.0)", https://www.digitraffic.fi).
Kategori Türkçe etiketleri `mw_catalog.CATEGORY_LABELS` (radio = **Radyo**); yönetici listesi `category_labels` olarak döner.

## 3. Veri modeli (hesap servisi `sshm.db`)

```sql
CREATE TABLE IF NOT EXISTS mw_sources (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,          -- 'adsb-lol' (ad'dan türetilir; içe aktarma anahtarı; [a-z0-9-]{2,40})
  category TEXT NOT NULL,             -- §2
  kind TEXT NOT NULL,                 -- §2
  name TEXT NOT NULL,                 -- Excel Kaynak
  data_desc TEXT, endpoint TEXT, protocol TEXT, auth TEXT, push_pull TEXT, scale TEXT, license TEXT, note TEXT,  -- Excel sütunları (bilgi)
  adapter TEXT,                       -- masterworld sunucusundaki adaptör anahtarı; NULL = yalnız katalog (haritada çizilmez)
  params TEXT NOT NULL DEFAULT '{}',  -- adaptör parametreleri JSON (≤ 4 KB)
  api_key TEXT,                       -- YALNIZ YAZILIR: yönetici listesinde has_key döner, değer asla dönmez (yalnız §3.3 iç uç)
  key_required INTEGER NOT NULL DEFAULT 0,   -- kimlik doğrulama/anahtar gerektirir
  noncommercial INTEGER NOT NULL DEFAULT 0,  -- ticari kullanım kısıtlı (Excel'de turuncu)
  attribution_required INTEGER NOT NULL DEFAULT 0,
  attribution TEXT,                   -- haritada gösterilecek atıf metni (ör. "© adsb.lol (ODbL)")
  attribution_url TEXT,
  rate_per_min REAL,                  -- kaynağa giden en fazla istek/dk (NULL = adaptör varsayılanı); sunucu bunu aşmaz
  ttl_s INTEGER,                      -- önbellek süresi (NULL = adaptör varsayılanı)
  enabled INTEGER NOT NULL DEFAULT 0, -- yalnız enabled=1 VE adapter dolu VE (key_required=0 YA DA api_key dolu) haritada
  default_on INTEGER NOT NULL DEFAULT 0, -- ilk açılışta görünür mü (kullanıcı ayarı yoksa)
  sort INTEGER NOT NULL DEFAULT 100,
  origin TEXT NOT NULL DEFAULT 'manual',   -- excel | builtin | manual
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mw_points (   -- tekil noktalar (elle eklenen kamera / radyo …): adapter='points' olan kaynağa bağlı
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES mw_sources(id) ON DELETE CASCADE,
  name TEXT NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL,
  media_type TEXT,                    -- image | mjpeg | audio | link | NULL
  media_url TEXT,                     -- https:// zorunlu; görüntüler sunucu vekilinden geçer, ses doğrudan çalınır (§5)
  props TEXT NOT NULL DEFAULT '{}',   -- serbest JSON (≤ 2 KB): ülke, açıklama, yenileme_s …
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mw_profiles (user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, profile TEXT NOT NULL, updated_at TEXT NOT NULL);
```

### 3.1 Excel içe aktarma (idempotent)

`sshm/mw_catalog.py`: stdlib xlsx okuyucu (zipfile + ElementTree; openpyxl YOK), ilk sayfa ("Kaynaklar") başlık satırı sütun adlarıyla eşlenir
(Kategori, Kaynak, Veri, Erişim / Endpoint, Protokol, Kimlik Doğrulama, Push / Pull, Ölçek / Güncelleme, Lisans / Ticari Kullanım, Not).
`slug` = Kaynak adından (Türkçe karakter sadeleştirme, `[a-z0-9-]`, ilk `/`ya da `(` öncesi). Yerleşik katalog `KNOWN[slug]` → `kind,
adapter, params, attribution, attribution_url, default_on, rate_per_min, ttl_s` önerileri; bilinmeyen satır: kind = kategorinin ilk türü,
adapter NULL. Bayraklar metinden: `key_required` (Kimlik Doğrulama "Yok" ile başlamıyorsa), `noncommercial` (lisans "ticari olmayan" /
"ticari için" / "non-commercial" / "NC" / "kişisel" içerir), `attribution_required` (lisans "atıf" / "CC BY" / "ODbL" içerir).
**Yeniden çalıştırma:** var olan slug'da yalnız Excel bilgi sütunları ve bayraklar güncellenir; `enabled, api_key, sort, default_on, params,
adapter (dolu ise), attribution (elle değiştiyse)` KORUNUR. Yeni slug eklenir (`enabled` = adaptör var VE anahtar gerekmiyorsa 1). Excel'de olmayan
kayıt SİLİNMEZ. Yerleşik ek kaynaklar (`origin='builtin'`) her içe aktarmada yoksa eklenir. Dönüş `{added, updated, unchanged, skipped:[{row, reason}]}`.
Uç: Merkez yükleme (≤ 5 MB, .xlsx imzası `PK`), ayrıca `python -m sshm.mw_catalog <dosya.xlsx>` (aynı işlev; önce `data/sshm-pre-mw-<ts>.db` yedeği —
Merkez yüklemesi de içe aktarmadan önce aynı yedeği alır). Ticari kısıt metin kuralına ek olarak **hücre rengiyle** de belirlenir: Lisans hücresinin
dolgusu (styles.xml cellXfs → fills, tema rengi dahil) ya da turuncu dolgulu koşullu biçim kuralı (`SEARCH("…")` / `containsText`) eşleşirse `noncommercial=1`.
Var olan kayıtta boş olan `adapter, attribution, attribution_url, rate_per_min, ttl_s` yerleşik katalogdan doldurulur; `kind` ve `category` dışındaki
elle alanlar korunur (`category` Excel'den güncellenir).

### 3.2 Yönetici uçları (hesap servisi; `X-Central-Secret`, mevcut `central(request)`)

- `GET /api/sm/admin/mw/sources` → `{sources:[… api_key yerine has_key; ayrıca live, key_missing, points (nokta sayısı), params nesne …], adapters:[…bilinen adaptör
  anahtarları…], categories:{category:[kind…]}, category_labels, kinds, media_types, stats:{total, enabled, live, key_missing}}` (`key_missing` = adaptörlü + anahtar gerekli + anahtar yok)
- `POST /api/sm/admin/mw/sources` (201) · `PUT /api/sm/admin/mw/sources/{id}` (kısmi; `api_key: ""` siler, `null`/yok = dokunma) · `DELETE …/{id}`
- `POST /api/sm/admin/mw/import` (multipart `file`) → §3.1 sonucu
- `GET/POST /api/sm/admin/mw/sources/{id}/points`, `PUT/DELETE /api/sm/admin/mw/points/{pid}`
- Doğrulama: slug deseni, category/kind sözlükte (kind kategoriden bağımsız, tüm türler), params/props JSON nesnesi ve boyut, attribution_url `https?://` ve ≤ 500,
  media_url yalnız `https://` (§3 tablo yorumu), endpoint bilgi alanıdır (Excel'de `gcmb.io`, `wss://…`, düz metin var): şema içeriyorsa yalnız
  http/https/ws/wss, ≤ 500; adapter `[a-z0-9_]{2,40}` (bilinen listeyle sınırlanmaz), metinler ≤ 500, lat −90..90 lon −180..180, rate_per_min 0.1–600,
  ttl_s 5–86400 (tam sayı). Hata `Err(422,'invalid',…)`; slug çakışması 409 `exists`. `origin` API'den yazılamaz (elle = `manual`).
  Nokta ekleme yalnız `adapter='points'` kaynakta.
- Merkez vekil uçları (`app/routers/sshmaster_admin.py`): `/api/central/sshm/mw/...` aynı yollar, `audit` kaydı (anahtar değeri audit'e YAZILMAZ).

### 3.3 İç uç (masterworld sunucusu → hesap servisi)

`GET /api/mw/internal/sources` başlık `X-Masterworld-Secret` (= `MASTERWORLD_MT_SHARED_SECRET`, iki tarafın .env'inde aynı; `hmac.compare_digest`)
→ `{version: <en son updated_at>, sources:[{id, slug, category, kind, name, data_desc, adapter, params, api_key, key_required, noncommercial,
attribution_required, attribution, attribution_url, license, rate_per_min, ttl_s, enabled, default_on, sort, scale}], points:{<source_id>:[{id,
name, lat, lon, media_type, media_url, props}]}}` — yalnız `enabled=1` kaynaklar ve noktaları; katalog satırları (adapter NULL) de `enabled=1`
ise "Kaynaklar" listesinde atıf/bilgi için döner. Yanıt `Cache-Control: no-store`; bu uç CORS'a kapalıdır (yalnız sunucular arası). `version` silmelerde
değişmeyebilir — masterworld sunucusu her çekişte kopyayı bütünüyle değiştirir.

## 4. masterworld sunucusu REST (anonim; JSON)

- `GET /api/meta` → `{version, mt_url, mt_app:'mw', ga_id, langs}`
- `GET /api/layers` → `{categories:[{key, sources:[{slug, kind, name, desc, attribution, attribution_url, license, noncommercial,
  attribution_required, live (adapter çalışır), mode, refresh_s, default_on}]}], catalog:[… çizilmeyen kaynaklar …]}` (api_key ASLA)
- `GET /api/data/{slug}?bbox=w,s,e,n&z=<zoom>` → `{slug, kind, mode, items:[{id, lat, lon, alt?, name, hdg?, spd?, t?, p:{…}}], lines?:[{id,
  coords:[[lon,lat]…], name, p}], fetched_at, ttl, attribution, truncated?}`
  - `mode`: `global` (tek anlık görüntü, bbox yok sayılır), `bbox` (görünüm alanı; sunucu bbox'ı ızgara hücrelerine yuvarlar ve hücre başına önbellek
    tutar — aynı bölgeye bakan tüm kullanıcılar aynı önbelleği paylaşır), `point` (`?lat&lon`; tıklanan nokta bilgisi, ör. hava tahmini).
  - item sayısı en fazla 5000 (aşarsa seyreltilir, `truncated: true`).
- `GET /api/tile/{slug}/{z}/{x}/{y}` → raster karo vekili (radar vb.; z ≤ 8; önbellek; yalnız adaptörün sabit karo şablonu).
- `GET /api/media/{slug}/{item_id}` → kamera görüntüsü vekili (JPEG/PNG/WebP; ≤ 2 MB; önbellek ≥ 10 sn; içerik türü doğrulanır).
- Radyo için ayrı uç YOK: akış adresi öğenin `p.stream` alanındadır (yalnız https), ses tarayıcıda doğrudan çalınır
  (§5; yayıncı akışını vekillemek bant genişliği + yeniden yayın sorunu olur).

### 4.1 Adaptör arayüzü (`app/sources/<ad>.py`)

```python
META = {'mode': 'global'|'bbox'|'point'|'tile', 'ttl': 30, 'rate_per_min': 30, 'burst': 1, 'hosts': ('api.adsb.lol',), 'kind': 'aircraft', 'needs_key': False}
async def fetch(ctx, src, q) -> dict   # ctx.get_json(url, headers=…) / ctx.get_bytes / ctx.get_text — yalnız META['hosts'] ve https
```
`ctx` istekleri: host beyaz listesi (adaptörün `hosts`'u), DNS çözümü sonrası özel/iç ağ adresi reddi (127/8, 10/8, 172.16/12, 192.168/16, 169.254/16,
100.64/10, ::1, fc00::/7, fe80::/10), yönlendirme izlenmez ya da her adımda aynı denetim, yanıt ≤ 8 MB (büyük statik veri kümeleri adaptörde
açıkça ≤ 40 MB), süre ≤ 15 sn, kaynak başına token bucket (`rate_per_min`), aynı anahtara eşzamanlı istekler tek istekte birleştirilir (singleflight),
hata sonrası üstel geri çekilme; `burst` = tek yenilemede birden çok dosya isteyen adaptörün kova kapasitesi; oran/TTL varsayılanı adaptör META'sıdır (kayıttaki `rate_per_min`/`ttl_s` doluysa onu ezer); kaynak hatası istemciye `{error:'source_unavailable'}` + son başarılı önbellek (varsa, `stale: true`).

## 5. Güvenlik (tüm dünyaya açık servis)

- Açık vekil yok: `slug` yalnız kayıttaki etkin kaynaklar; URL istemciden ALINMAZ (yalnız bbox/z/lat/lon sayısal, sınırlı).
- IP başına oran sınırı (`cf-connecting-ip`): veri 120/dk, medya 60/dk, karo 600/dk → 429 + `Retry-After`.
- CSP: `default-src 'self'`; script `'self' https://www.googletagmanager.com https://static.cloudflareinsights.com` (inline YOK); style `'self'`;
  img `'self' data: blob: https://gibs.earthdata.nasa.gov https://tiles.openfreemap.org`; connect `'self' https://mastertool.download https://tiles.openfreemap.org
  https://gibs.earthdata.nasa.gov` + GA; media `https:` (radyo akışları); worker `blob:`; `frame-ancestors 'none'`.
- Hata yanıtları tek tip (`{error:<kod>}`); kaynak adresi / istisna metni sızdırılmaz. API anahtarları istemciye, günlüğe ve audit'e yazılmaz.
- Ticari kısıtlı (`noncommercial`) ve atıf zorunlu kaynaklar arayüzde rozetle işaretlenir; görünür her katmanın atfı köşedeki atıf kutusunda.

## 6. Yayın

Depo `goktalay/masterworld`: `v*` etiketi → `.github/workflows/release.yml` (testler, `masterworld-<v>.tar.gz` + sha256, GitHub Release,
`scripts/upload-mastertool.sh` → `POST https://mastertool.download/api/mw/web-releases` `X-Release-Key: $MASTERWORLD_RELEASE_KEY`) →
hesap servisi `data/releases/mw/<v>/` + `latest` (paket kökünde `VERSION`, `requirements.txt`, **`run-masterworld.sh`** zorunlu; SIMUMAV'daki
`run-simumav.sh` kuralının karşılığı) → PROD `hepgo-masterworld-deploy.path` → `deploy/masterworld/deploy.sh` (sha256, güvenli açma,
rsync -ac, sağlık `/api/meta`, geri dönüş). Hesap servisi: `RELEASE_KEYS['mw']` = `MASTERWORLD_RELEASE_KEY`, `WEB_RELEASE_APPS['mw'] = 'masterworld'`.

## 7. Mastertool kataloğu

`GAMES['mw'] = {'name': 'MASTERWORLD', 'slug': 'masterworld', 'icon': 'masterworld', 'site': 'https://masterworld.app', 'promo': 'https://masterworld.app/',
'group': 'apps'}` + 8 dil `desc`; `/api/mt/apps?web=1` ve `/uygulamalar` başlatıcısında kart (kendi sitesine açılır), mastertool.download ana sayfasında kart,
`/oyunlar/masterworld*` → 307 masterworld.app. Simge `static/mt/img/masterworld.svg|.png|-512.png` (`tools/masterworld_brand.py`), `/brand/mw.svg|.png|-512.png`.
`group:'apps'` olduğu için `/uygulamalar` başlatıcısında "Uygulamalar" bölümünde ("Aç", yeni sekmede kendi sitesi), Hesabım'da "Web uygulamaları" başlığı
altında (Ayarlar: hesapta kayıtlı / yok); Merkez › Mastertool kullanıcı özeti `games.mw = {has_profile, last_at}`, üst kart `stats.games.mw = {name, users, release}`.
Giriş/kayıt `?app=mw` ile gelince dönüş adresi https://masterworld.app/ (hesap.js `GAME_URLS`).

## 8. DNS (kullanıcı)

Cloudflare › masterworld.app › DNS: `CNAME @ → 294f79b9-1cf7-4cbc-b806-a7f70a1e0404.cfargotunnel.com` (Proxied) ve `CNAME www → aynı` (Proxied).
