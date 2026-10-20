# MASTERWORLD — canlı veri küresi (masterworld.app)

Kamuya açık canlı veri kaynaklarını (uçak, uydu, deprem, kamera, radyo, hava durumu …) tam ekran 3B küreye yerleştiren web uygulaması.
Üyelik isteğe bağlıdır (mastertool.download hesabı, uygulama kodu `mw`); üye olmayanın ayarları tarayıcıda, üyeninki hesabında saklanır.

- **Ön yüz:** `static/` — MapLibre GL JS 6.15.0 (yerel `static/vendor/maplibre-gl`, BSD-3), küre projeksiyonu, OpenFreeMap vektör altlık,
  NASA GIBS raster altlıklar (gece ışıkları, Blue Marble, dünün uydu mozaiği). Modüller: `js/app.js` (giriş), `map.js`, `layers.js` (katman yöneticisi,
  kümeleme, ölü hesap, uydu yörüngesi), `sat.js` (Kepler + J2), `cards.js` (kamera önizleme, uçak/deprem/uydu kartı, hava durumu, radyo çalar),
  `auth.js` + `settings.js` (isteğe bağlı üyelik, ayar senkronu), `analytics.js` (GA4 + rıza bandı), `i18n.js` + `i18n/*.json` (8 dil).
- **Sunucu:** `app/` — FastAPI. Kaynak kaydı hesap servisinin iç ucundan (`/api/mw/internal/sources`, paylaşılan gizli) dakikada bir çekilir.
  `app/sources/<adaptör>.py` kaynak adaptörleri; `app/fetch.py` güvenli istemci (https + host beyaz listesi, iç ağ reddi, boyut/süre sınırı,
  kaynak başına token bucket, paylaşılan önbellek, singleflight); `app/engine.py` katman verisi (global / bbox hücreleri / nokta / karo), medya ve karo vekili.
- **Uçlar (anonim):** `GET /api/meta`, `/api/layers`, `/api/data/{slug}?bbox=|lat&lon`, `/api/media/{slug}/{id}`, `/api/tile/{slug}/{z}/{x}/{y}`.
- Sözleşme: `docs/sozlesme.md` (HEPGO deposundaki `docs/masterworld.md` kopyası).

## Geliştirme

```bash
python3 tests/dev_sources.py                 # hesap servisi olmadan örnek kaynak kaydı → /tmp/masterworld-dev-sources.json
MW_SOURCES_FILE=/tmp/masterworld-dev-sources.json ./run-masterworld.sh     # http://127.0.0.1:8650
MW_OFFLINE=1 python -m unittest tests.test_sources -v                      # ağsız adaptör + güvenlik testleri
python -m tests.live_smoke                                                 # canlı kaynaklara tek çağrı (kibar)
python tests/shots.py http://127.0.0.1:8650 /tmp/masterworld/shots         # Playwright ekran görüntüleri
```

Ortam: `MW_DATA_DIR`, `MW_MT_URL` (tarayıcının gideceği hesap servisi; CSP connect-src'ye girer), `MW_MT_INTERNAL`, `MW_MT_SHARED_SECRET`
(hesap servisindeki `MASTERWORLD_MT_SHARED_SECRET` ile aynı), `MW_GA_ID`, `MW_UDS` (PROD Unix soketi).

Simge sprite'ı: `python3 scripts/build_icons.py` (`static/js/icons.js` → `static/img/icons.svg`, `favicon.svg`).

## Yayın

`v1.2.3` etiketi → `.github/workflows/release.yml` (testler, `masterworld-<v>.tar.gz` + sha256, GitHub Release) → `scripts/upload-mastertool.sh`
(`POST https://mastertool.download/api/mw/web-releases`, `X-Release-Key: $MASTERWORLD_RELEASE_KEY` — depo secret'ı) → PROD
`hepgo-masterworld-deploy.path` → `deploy/masterworld/deploy.sh` (sha256, güvenli açma, rsync -ac, sağlık `/api/meta`, geri dönüş).
Kurulum birimleri ve cloudflared parçası: `deploy/masterworld/`.
