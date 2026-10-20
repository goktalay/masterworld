"""EMSC SeismicPortal — FDSN event, JSON (GeoJSON); son 24 saat, en çok 500 olay (CC BY 4.0; atıf "EMSC")."""
import time

from . import clip, num, ok_coord, safe_id, clean
from ._quake import iso_ts, utc_str
from ..fetch import FetchError

META = {'mode': 'global', 'ttl': 120, 'rate_per_min': 4, 'hosts': ('www.seismicportal.eu',), 'kind': 'quake', 'needs_key': False,
        'refresh_s': 120}


async def fetch(ctx, src, q):
    start = utc_str(time.time() - 86400)
    d = await ctx.get_json(f'https://www.seismicportal.eu/fdsnws/event/1/query?format=json&limit=500&orderby=time&start={start}')
    if not isinstance(d, dict) or not isinstance(d.get('features'), list):
        raise FetchError('emsc: beklenmeyen biçim')
    out = []
    for f in d['features']:
        p = (f or {}).get('properties') or {}
        lat, lon = num(p.get('lat')), num(p.get('lon'))
        if not ok_coord(lat, lon):
            continue
        fid = safe_id(p.get('unid') or f.get('id'))
        if not fid:
            continue
        mag = num(p.get('mag'))
        out.append({'id': fid, 'lat': lat, 'lon': lon, 'name': clip((p.get('flynn_region') or '').title(), 120) or 'Deprem',
                    't': iso_ts(p.get('time')),
                    'p': clean({'mag': mag, 'depth_km': num(p.get('depth')), 'type': clip(p.get('magtype'), 6), 'auth': clip(p.get('auth'), 12),
                                'url': f'https://www.seismicportal.eu/eventdetails.html?unid={fid}'})})
    return {'items': out}
