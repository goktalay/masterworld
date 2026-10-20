"""Submarine Cable Map (TeleGeography) — denizaltı kablo güzergâhları (çizgi) + karaya çıkış noktaları (öğe).
Lisans CC BY-NC-SA 3.0 → atıf "© TeleGeography, submarinecablemap.com", ticari olmayan. ttl 1 gün."""
from . import clip, num, ok_coord, safe_id, clean, paced
from ..fetch import FetchError

META = {'burst': 2, 'mode': 'global', 'ttl': 86400, 'rate_per_min': 12, 'hosts': ('www.submarinecablemap.com',), 'kind': 'cable', 'needs_key': False,
        'refresh_s': 86400}
BASE = 'https://www.submarinecablemap.com/api/v3'
MAX_PTS = 4000          # parça başına nokta


def _coords(part):
    out = []
    for c in part if isinstance(part, list) else []:
        if isinstance(c, list) and len(c) >= 2:
            lon, lat = num(c[0]), num(c[1])
            if lon is not None and lat is not None and -90 <= lat <= 90 and -180.5 <= lon <= 180.5:
                out.append([round(max(-180.0, min(180.0, lon)), 4), round(lat, 4)])
    return out[:MAX_PTS]


def lines(d):
    if not isinstance(d, dict) or not isinstance(d.get('features'), list):
        raise FetchError('submarine_cables: kablo verisi beklenmeyen biçimde')
    out = []
    for f in d['features']:
        p = (f or {}).get('properties') or {}
        g = f.get('geometry') or {}
        parts = g.get('coordinates') if g.get('type') == 'MultiLineString' else [g.get('coordinates')] if g.get('type') == 'LineString' else []
        cid = safe_id(p.get('id'), 60)
        if not cid:
            continue
        color = str(p.get('color') or '')
        for i, part in enumerate(parts or []):
            cs = _coords(part)
            if len(cs) >= 2:
                out.append({'id': f'{cid}~{i}', 'coords': cs, 'name': clip(p.get('name'), 100) or cid,
                            'p': clean({'color': color if len(color) in (4, 7) and color.startswith('#') else None, 'cable': cid,
                                        'url': f'https://www.submarinecablemap.com/submarine-cable/{cid}'})})
    return out


def landings(d):
    if not isinstance(d, dict) or not isinstance(d.get('features'), list):
        raise FetchError('submarine_cables: çıkış noktası verisi beklenmeyen biçimde')
    out = []
    for f in d['features']:
        p = (f or {}).get('properties') or {}
        c = ((f or {}).get('geometry') or {}).get('coordinates') or []
        lon, lat = (num(c[0]), num(c[1])) if len(c) >= 2 else (None, None)
        lid = safe_id(p.get('id'), 70)
        if not ok_coord(lat, lon) or not lid:
            continue
        out.append({'id': f'lp~{lid}', 'lat': lat, 'lon': lon, 'name': clip(p.get('name'), 100) or lid,
                    'p': clean({'landing': True, 'tbd': True if p.get('is_tbd') else None,
                                'url': f'https://www.submarinecablemap.com/landing-point/{lid}'})})
    return out


async def fetch(ctx, src, q):
    ln = lines(await ctx.get_json(f'{BASE}/cable/cable-geo.json'))
    lp = landings(await paced(ctx, lambda: ctx.get_json(f'{BASE}/landing-point/landing-point-geo.json')))
    return {'items': lp, 'lines': ln}
