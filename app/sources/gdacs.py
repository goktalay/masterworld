"""GDACS — Küresel Afet Uyarı ve Koordinasyon Sistemi (AB JRC / BM). gdacsapi EVENTS4APP: güncel olaylar GeoJSON (nokta).
p: eventtype (EQ deprem, TC kasırga, FL sel, VO yanardağ, DR kuraklık, WF orman yangını, TS tsunami), alertlevel, url (rapor)."""
from . import clip, num, ok_coord, safe_id, clean
from ._quake import iso_ts
from ..fetch import FetchError

META = {'mode': 'global', 'ttl': 600, 'rate_per_min': 2, 'hosts': ('www.gdacs.org',), 'kind': 'disaster', 'needs_key': False,
        'refresh_s': 600}
RANK = {'green': 1, 'orange': 2, 'red': 3}


async def fetch(ctx, src, q):
    d = await ctx.get_json('https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP')
    if not isinstance(d, dict) or not isinstance(d.get('features'), list):
        raise FetchError('gdacs: beklenmeyen biçim')
    out, seen = [], set()
    for f in d['features']:
        g = (f or {}).get('geometry') or {}
        p = f.get('properties') or {}
        c = g.get('coordinates') if g.get('type') == 'Point' else None
        if not c:
            bb = f.get('bbox') or []
            c = [(num(bb[0], 0) + num(bb[2], 0)) / 2, (num(bb[1], 0) + num(bb[3], 0)) / 2] if len(bb) == 4 else None
        lon, lat = (num(c[0]), num(c[1])) if c and len(c) >= 2 else (None, None)
        et = clip(p.get('eventtype'), 4)
        fid = safe_id(f"{et}{p.get('eventid')}")
        if not ok_coord(lat, lon) or not fid or fid in seen:
            continue
        seen.add(fid)
        al = str(p.get('alertlevel') or '').lower() or None
        url = ((p.get('url') or {}).get('report') if isinstance(p.get('url'), dict) else None) or ''
        out.append({'id': fid, 'lat': lat, 'lon': lon, 'name': clip(p.get('name'), 120) or 'Afet', 't': iso_ts(p.get('fromdate')),
                    'p': clean({'eventtype': et, 'alertlevel': al, 'rank': RANK.get(al), 'country': clip(p.get('country'), 80),
                                'severity': clip((p.get('severitydata') or {}).get('severitytext'), 80),
                                'to': clip(p.get('todate'), 20), 'url': clip(url, 200) if url.startswith('https://') else None})})
    return {'items': out}
