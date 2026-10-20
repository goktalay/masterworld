"""AFAD Deprem Dairesi — olay filtresi (son 24 saat). Eski deprem.afad.gov.tr/apiv2 adresi 302 ile
servisnet.afad.gov.tr/apigateway/deprem/apiv2'ye yönlendiriyor (yönlendirme izlenmez → doğrudan güncel adres).
Tarihler UTC (ör. 2026-10-20T10:25:48)."""
import time

from . import clip, num, ok_coord, safe_id, clean
from ._quake import iso_ts, utc_str
from ..fetch import FetchError

META = {'mode': 'global', 'ttl': 120, 'rate_per_min': 4, 'hosts': ('servisnet.afad.gov.tr',), 'kind': 'quake', 'needs_key': False,
        'refresh_s': 120}
BASE = 'https://servisnet.afad.gov.tr/apigateway/deprem/apiv2/event/filter'


async def fetch(ctx, src, q):
    now = time.time()
    d = await ctx.get_json(f'{BASE}?start={utc_str(now - 86400)}&end={utc_str(now + 60)}&format=json&orderby=timedesc&limit=500')
    if not isinstance(d, list):
        raise FetchError('afad: beklenmeyen biçim')
    out = []
    for e in d[:2000]:
        if not isinstance(e, dict):
            continue
        lat, lon = num(e.get('latitude')), num(e.get('longitude'))
        eid = safe_id(e.get('eventID'))
        if not ok_coord(lat, lon) or not eid:
            continue
        out.append({'id': eid, 'lat': lat, 'lon': lon, 'name': clip(e.get('location'), 120) or 'Deprem', 't': iso_ts(e.get('date')),
                    'p': clean({'mag': num(e.get('magnitude')), 'depth_km': num(e.get('depth')), 'type': clip(e.get('type'), 6),
                                'country': clip(e.get('country'), 40), 'province': clip(e.get('province'), 40),
                                'url': f'https://deprem.afad.gov.tr/event-detail/{eid}'})})
    return {'items': out}
