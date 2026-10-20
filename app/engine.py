"""Katman verisi üretimi: kayıt + adaptör + paylaşılan önbellek. İstemciye giden her şey buradan geçer (gizli alanlar ayıklanır)."""
import math
import time

from . import config, fetch, registry
from .sources import ADAPTERS

import logging

log = logging.getLogger('masterworld.engine')
_logged = {}          # slug → son günlük zamanı (kaynak hatası en çok dakikada bir yazılır)


def _warn(slug, e):
    now = time.time()
    if now - _logged.get(slug, 0) > 60:
        _logged[slug] = now
        log.warning('kaynak hatası: %s', e)


_media = {}           # slug → {öğe id → görüntü adresi} (vekil için; istemciye verilmez)
MEDIA_MAX = 50000


class NotFound(Exception):
    pass


class Unavailable(Exception):
    pass


def adapter_of(src):
    return ADAPTERS.get(src.get('adapter') or '') if src else None


def meta_of(src):
    a = adapter_of(src)
    return a.META if a else None


def is_live(src):
    m = meta_of(src)
    return bool(src and src.get('enabled') and m and (not (src.get('key_required') or m.get('needs_key')) or src.get('api_key')))


def live_source(slug):
    src = registry.get(slug)
    if not is_live(src):
        raise NotFound(slug)
    return src


def ttl_of(src):
    m = meta_of(src)
    return int(src.get('ttl_s') or m.get('ttl', 60))


def ctx_of(src):
    m = meta_of(src)
    return fetch.Ctx(src['slug'], m.get('hosts'), src.get('rate_per_min') or m.get('rate_per_min', 30),
                     any_host=bool(m.get('any_host')), api_key=src.get('api_key'), burst=m.get('burst', 1))


def _remember_media(slug, items):
    d = _media.setdefault(slug, {})
    for it in items:
        if it.get('_media'):
            d[str(it['id'])] = it['_media']
    if len(d) > MEDIA_MAX:
        for k in list(d)[:len(d) - MEDIA_MAX]:
            d.pop(k, None)


def _public(items):
    out = []
    for it in items:
        o = {k: v for k, v in it.items() if not k.startswith('_') and v is not None}
        if it.get('_media'):
            o.setdefault('p', {})['media'] = 'image'
        out.append(o)
    return out


def _in_bbox(it, bbox):
    w, s, e, n = bbox
    if not (s <= it['lat'] <= n):
        return False
    return (w <= it['lon'] <= e) if w <= e else (it['lon'] >= w or it['lon'] <= e)


def _thin(items, bbox, cap):
    """Seyreltme: en önemliler önce (p.rank / mag / votes), sonra uzamsal düzgün örnekleme."""
    if len(items) <= cap:
        return items, False
    def key(it):
        p = it.get('p') or {}
        return -(p.get('rank') or p.get('mag') or p.get('votes') or 0)
    items = sorted(items, key=key)
    head, rest = items[:cap // 2], items[cap // 2:]
    step = len(rest) / (cap - len(head))
    return head + [rest[int(i * step)] for i in range(cap - len(head))], True


def parse_bbox(v):
    try:
        w, s, e, n = (float(x) for x in str(v).split(','))
    except (TypeError, ValueError):
        return (-180.0, -90.0, 180.0, 90.0)
    if not all(math.isfinite(x) for x in (w, s, e, n)):
        return (-180.0, -90.0, 180.0, 90.0)
    s, n = max(-90.0, min(s, n)), min(90.0, max(s, n))
    if e - w >= 360:
        w, e = -180.0, 180.0
    w = ((w + 180) % 360) - 180
    e = ((e + 180) % 360) - 180 if e != 180 else 180.0
    return (w, s, e, n)


def _cells(bbox, deg, max_cells):
    w, s, e, n = bbox
    lat_c, lon_c = (s + n) / 2, ((w + e) / 2 if w <= e else ((w + e + 360) / 2 + 180) % 360 - 180)
    lons = []
    i0 = math.floor(w / deg)
    i1 = math.floor((e if w <= e else e + 360) / deg)
    for i in range(i0, i1 + 1):
        lons.append((((i * deg) + 180) % 360) - 180)
    lats = [j * deg for j in range(math.floor(s / deg), math.floor(min(n, 89.999) / deg) + 1)]
    cells = [(x, y, x + deg, y + deg) for x in lons for y in lats]
    cells.sort(key=lambda c: (c[1] + deg / 2 - lat_c) ** 2 + (((c[0] + deg / 2 - lon_c + 540) % 360) - 180) ** 2)
    return cells[:max_cells], len(cells) > max_cells


async def data(slug, bbox=None, lat=None, lon=None):
    src = live_source(slug)
    a, m = adapter_of(src), meta_of(src)
    mode, ttl = m.get('mode', 'global'), ttl_of(src)
    bbox = bbox or (-180.0, -90.0, 180.0, 90.0)
    stale = truncated = False
    items, lines = [], []
    ctx = ctx_of(src)
    if mode == 'global':
        try:
            res, stale = await fetch.cached(f'g:{slug}', ttl, lambda: a.fetch(ctx, src, {}))
        except fetch.FetchError as e:
            _warn(slug, e)
            raise Unavailable(slug) from None
        _remember_media(slug, res.get('items') or [])
        items = [it for it in res.get('items') or [] if _in_bbox(it, bbox)]
        lines = res.get('lines') or []
    elif mode == 'bbox':
        deg = float(m.get('cell_deg', 5))
        cells, truncated = _cells(bbox, deg, int(m.get('max_cells', 9)))
        ok = limited = 0
        seen = set()
        for c in cells:
            q = {'cell': c, 'lat': c[1] + deg / 2, 'lon': c[0] + deg / 2,
                 'radius_nm': min(250, math.ceil(math.hypot(deg / 2, deg / 2 * math.cos(math.radians(min(85, abs(c[1] + deg / 2))))) * 60) + 5)}
            try:
                res, st = await fetch.cached(f'b:{slug}:{c[0]}:{c[1]}', ttl, lambda q=q: a.fetch(ctx, src, q))
            except fetch.RateLimited:   # kendi oran sınırımız: hücre bu turda atlanır (kaynak hatası sayılmaz)
                limited += 1
                continue
            except fetch.FetchError as e:
                _warn(slug, e)
                continue
            ok += 1
            stale = stale or st
            _remember_media(slug, res.get('items') or [])
            for it in res.get('items') or []:
                if it['id'] not in seen and _in_bbox(it, bbox):
                    seen.add(it['id'])
                    items.append(it)
        if limited:
            truncated = True
        if cells and not ok and not limited:
            raise Unavailable(slug)
    elif mode == 'point':
        if lat is None or lon is None:
            raise NotFound(slug)
        q = {'lat': round(lat, 1), 'lon': round(lon, 1)}
        try:
            res, stale = await fetch.cached(f'p:{slug}:{q["lat"]}:{q["lon"]}', ttl, lambda: a.fetch(ctx, src, q))
        except fetch.FetchError:
            raise Unavailable(slug) from None
        items = res.get('items') or []
        return {'slug': slug, 'kind': src['kind'], 'mode': mode, 'items': _public(items), 'data': res.get('data'),
                'fetched_at': int(time.time()), 'ttl': ttl, 'stale': stale or None}
    else:
        raise NotFound(slug)
    items, thinned = _thin(items, bbox, config.MAX_ITEMS)
    out = {'slug': slug, 'kind': src['kind'], 'mode': mode, 'items': _public(items), 'fetched_at': int(time.time()), 'ttl': ttl}
    if lines:
        out['lines'] = lines
    if stale:
        out['stale'] = True
    if truncated or thinned:
        out['truncated'] = True
    return out


async def media(slug, item_id):
    """Kamera görüntüsü (bayt, içerik türü). Adres yalnız sunucunun daha önce kaynaktan aldığı öğe dizininden."""
    src = live_source(slug)
    a = adapter_of(src)
    url = _media.get(slug, {}).get(str(item_id))
    if not url and hasattr(a, 'media_url'):
        url = await a.media_url(ctx_of(src), src, {'id': str(item_id)})
    if not url:
        raise NotFound(item_id)
    ctx = ctx_of(src)
    mhosts = getattr(a, 'MEDIA_HOSTS', None)
    if mhosts is not None:
        ctx.hosts = tuple(mhosts)

    async def get():
        body, ctype = await ctx.get_bytes(url, max_bytes=2 * 1024 * 1024, accept='image/jpeg, image/png, image/webp, image/*;q=0.8')
        ctype = ctype.split(';')[0].strip().lower()
        if ctype not in ('image/jpeg', 'image/png', 'image/webp', 'image/gif'):
            if body[:3] == b'\xff\xd8\xff':
                ctype = 'image/jpeg'
            elif body[:8] == b'\x89PNG\r\n\x1a\n':
                ctype = 'image/png'
            else:
                raise fetch.FetchError(f'{slug}: görüntü değil ({ctype})')
        return body, ctype
    try:
        (body, ctype), _ = await fetch.cached(f'm:{slug}:{item_id}', max(10, min(ttl_of(src), 60)), get, stale=120)
    except fetch.FetchError:
        raise Unavailable(slug) from None
    return body, ctype


async def tile(slug, z, x, y):
    src = live_source(slug)
    a = adapter_of(src)
    if not hasattr(a, 'tile_url') or not (0 <= z <= int(a.META.get('max_zoom', 8))) or not (0 <= x < 2 ** z and 0 <= y < 2 ** z):
        raise NotFound(slug)
    ctx = ctx_of(src)

    async def get():
        url = await a.tile_url(ctx, src, z, x, y)
        body, ctype = await ctx.get_bytes(url, max_bytes=1024 * 1024, accept='image/png, image/webp, image/*;q=0.8')
        ctype = ctype.split(';')[0].strip().lower()
        if not ctype.startswith('image/'):
            raise fetch.FetchError(f'{slug}: karo görüntü değil')
        return body, ctype
    try:
        (body, ctype), _ = await fetch.cached(f't:{slug}:{z}:{x}:{y}', ttl_of(src), get, stale=ttl_of(src) * 3)
    except fetch.FetchError:
        raise Unavailable(slug) from None
    return body, ctype


def layers():
    """/api/layers: kategori → kaynaklar (yalnız etkin); çizilemeyenler katalog. api_key ASLA."""
    cats = {}
    catalog = []
    for s in sorted(registry.sources().values(), key=lambda s: (s.get('sort', 100), s.get('name', ''))):
        if not s.get('enabled'):
            continue
        m = meta_of(s)
        pub = {'slug': s['slug'], 'kind': s.get('kind'), 'category': s.get('category'), 'name': s.get('name'), 'desc': s.get('data_desc'),
               'attribution': s.get('attribution') or s.get('name'), 'attribution_url': s.get('attribution_url'), 'license': s.get('license'),
               'noncommercial': bool(s.get('noncommercial')), 'attribution_required': bool(s.get('attribution_required')),
               'scale': s.get('scale')}
        if is_live(s):
            pub |= {'live': True, 'mode': m.get('mode'), 'refresh_s': int(m.get('refresh_s', ttl_of(s))), 'default_on': bool(s.get('default_on')),
                    'max_zoom': m.get('max_zoom')}
            cats.setdefault(s.get('category') or 'other', []).append(pub)
        else:
            pub['live'] = False
            pub['reason'] = 'key_missing' if m and (s.get('key_required') or m.get('needs_key')) and not s.get('api_key') else 'catalog'
            catalog.append(pub)
    return {'version': registry.version(), 'categories': [{'key': k, 'sources': v} for k, v in cats.items()], 'catalog': catalog}
