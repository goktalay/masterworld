"""Safecast — gönüllü radyasyon ölçümleri (CC0). Son 24 saatin en yeni ≤ 1000 ölçümü, cihaz başına en yenisi.
p.value + p.unit (çoğunlukla cpm), p.rank = değer."""
import time

from . import clip, num, ok_coord, safe_id, clean
from ._quake import iso_ts
from ..fetch import FetchError

META = {'mode': 'global', 'ttl': 900, 'rate_per_min': 2, 'hosts': ('api.safecast.org',), 'kind': 'radiation', 'needs_key': False,
        'refresh_s': 900}


async def fetch(ctx, src, q):
    since = time.strftime('%Y-%m-%dT%H:%M', time.gmtime(time.time() - 86400))
    d = await ctx.get_json(f'https://api.safecast.org/measurements.json?captured_after={since}&order=captured_at+desc&per_page=1000')
    if not isinstance(d, list):
        raise FetchError('safecast: beklenmeyen biçim')
    out, seen = [], set()
    for m in d:
        if not isinstance(m, dict):
            continue
        lat, lon, v = num(m.get('latitude')), num(m.get('longitude')), num(m.get('value'))
        if not ok_coord(lat, lon) or v is None:
            continue
        dev = m.get('device_id') or m.get('sensor_id') or m.get('station_id')
        key = f'd{dev}' if dev else f'{lat:.3f},{lon:.3f}'
        mid = safe_id(m.get('id'))
        if key in seen or not mid:
            continue
        seen.add(key)
        unit = clip(m.get('unit'), 12)
        out.append({'id': mid, 'lat': lat, 'lon': lon, 'name': f'{v:g} {unit or ""}'.strip(), 't': iso_ts(m.get('captured_at')),
                    'p': clean({'value': v, 'unit': unit, 'rank': v, 'device': int(dev) if isinstance(dev, int) else None,
                                'place': clip(m.get('location_name'), 80), 'height': num(m.get('height'))})})
    return {'items': out}
