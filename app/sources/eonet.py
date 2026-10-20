"""NASA EONET v3 — açık doğal olaylar (orman yangını, fırtına, yanardağ, deniz buzu …; kamu malı).
Nokta = son geometri (çokgense ilk halkanın ağırlık merkezi); p.cat kategori kimliği. Yanıt ~5 MB → max_bytes 20 MB."""
from . import clip, num, ok_coord, safe_id, clean
from ._quake import iso_ts
from ..fetch import FetchError

META = {'mode': 'global', 'ttl': 1800, 'rate_per_min': 2, 'hosts': ('eonet.gsfc.nasa.gov',), 'kind': 'event', 'needs_key': False,
        'refresh_s': 1800}


def _point(g):
    c = g.get('coordinates')
    if g.get('type') == 'Point' and isinstance(c, list) and len(c) >= 2:
        return num(c[1]), num(c[0])
    if g.get('type') == 'Polygon' and isinstance(c, list) and c and isinstance(c[0], list):
        ring = [x for x in c[0] if isinstance(x, list) and len(x) >= 2 and num(x[0]) is not None and num(x[1]) is not None]
        if ring:
            return sum(num(x[1]) for x in ring) / len(ring), sum(num(x[0]) for x in ring) / len(ring)
    return None, None


async def fetch(ctx, src, q):
    d = await ctx.get_json('https://eonet.gsfc.nasa.gov/api/v3/events?status=open', max_bytes=20 * 1024 * 1024)
    if not isinstance(d, dict) or not isinstance(d.get('events'), list):
        raise FetchError('eonet: beklenmeyen biçim')
    out = []
    for e in d['events']:
        geo = [g for g in (e or {}).get('geometry') or [] if isinstance(g, dict)]
        if not geo:
            continue
        g = geo[-1]
        lat, lon = _point(g)
        eid = safe_id(e.get('id'))
        if not ok_coord(lat, lon) or not eid:
            continue
        cats = e.get('categories') or [{}]
        srcs = [s.get('url') for s in e.get('sources') or [] if isinstance(s, dict) and str(s.get('url') or '').startswith('https://')]
        out.append({'id': eid, 'lat': round(lat, 4), 'lon': round(lon, 4), 'name': clip(e.get('title'), 120) or 'Olay', 't': iso_ts(g.get('date')),
                    'p': clean({'cat': clip(cats[0].get('id'), 30), 'cat_name': clip(cats[0].get('title'), 40),
                                'mag': num(g.get('magnitudeValue')), 'mag_unit': clip(g.get('magnitudeUnit'), 12),
                                'url': clip(srcs[0], 200) if srcs else None})})
    return {'items': out}
