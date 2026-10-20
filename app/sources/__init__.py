"""Kaynak adaptörleri. Her modül:

    META = {'mode': 'global'|'bbox'|'point'|'tile', 'ttl': sn, 'rate_per_min': n, 'hosts': (...), 'kind': '...',
            'needs_key': bool, 'refresh_s': istemci yenileme (sn), 'cell_deg': bbox hücresi (derece), 'max_cells': n,
            'any_host': yalnız elle eklenen noktalar (points) için True}
    async def fetch(ctx, src, q) -> {'items': [...], 'lines': [...]}
        q: global → {} · bbox → {'cell': (w, s, e, n), 'lat', 'lon', 'radius_nm'} · point → {'lat', 'lon'}
        item: {'id', 'lat', 'lon', 'alt'?, 'name', 'hdg'?, 'spd'?, 't'?, 'p': {…görünür ayrıntılar…}, '_media'?: görüntü adresi (gizli; vekilden)}
        Ses akışları (radyo) p.stream içinde (https; tarayıcı doğrudan çalar — docs §4).
    async def tile_url(ctx, src, z, x, y) -> str        (yalnız mode 'tile')
    async def media_url(ctx, src, item) -> str          (isteğe bağlı: görüntü adresi her seferinde taze üretilecekse)

ctx: app.fetch.Ctx — get_json/get_text/get_bytes; yalnız META['hosts'] ve https; src: kayıt (params, api_key …).
"""
import importlib
import logging
import pkgutil

log = logging.getLogger('masterworld.sources')
ADAPTERS = {}


def load_all():
    for m in pkgutil.iter_modules(__path__):
        if m.name.startswith('_'):
            continue
        try:
            mod = importlib.import_module(f'{__name__}.{m.name}')
        except Exception:   # tek adaptörün hatası servisi düşürmesin
            log.exception('adaptör yüklenemedi: %s', m.name)
            continue
        if isinstance(getattr(mod, 'META', None), dict) and (hasattr(mod, 'fetch') or hasattr(mod, 'tile_url')):
            ADAPTERS[m.name] = mod
    return ADAPTERS


def num(v, default=None):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return x if x == x and abs(x) != float('inf') else default


def ok_coord(lat, lon):
    return lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180 and not (lat == 0 and lon == 0)


def clip(s, n=160):
    if s is None:
        return None
    s = str(s).strip()
    return s[:n] if s else None


_ID_BAD = __import__('re').compile(r'[^A-Za-z0-9_.:,~-]+')


def safe_id(v, n=80):
    """Öğe kimliği: ID_RE (^[A-Za-z0-9_.:,~-]{1,80}$) dışı karakterler '_' olur, uzunluk kırpılır; boşsa None."""
    if v is None:
        return None
    s = _ID_BAD.sub('_', str(v).strip()).strip('_')[:n]
    return s or None


def clean(d):
    """p sözlüğünden None / boş metin değerlerini atar (istemciye kısa ve temiz)."""
    return {k: v for k, v in d.items() if v is not None and v != ''}


async def paced(ctx, make, max_wait=30.0):
    """Birden çok istek atan adaptörler için: kaynak oran kovası boşsa (RateLimited) bir sonraki jeton kadar bekleyip
    yeniden dener (toplam ≤ max_wait sn). Kova kapasitesi rate_per_min/6 olduğundan düşük oranlı kaynakta 2. istek
    hemen reddedilir; bu yardımcı sınırı AŞMAZ, yalnız sıraya sokar. make: argümansız, awaitable döndüren işlev."""
    import asyncio
    from ..fetch import RateLimited
    waited = 0.0
    while True:
        try:
            return await make()
        except RateLimited:
            step = min(max_wait - waited, 1.0 / max(ctx.bucket.rate, 1e-6) + 0.05)
            if step <= 0:
                raise
            await asyncio.sleep(step)
            waited += step
