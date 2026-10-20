"""Sensor.Community (eski luftdaten) — PM2.5 / PM10 partikül sensörleri, son 5 dk ortalaması (ODbL; atıf).
data.dust.min.json (~5 MB, büyüyebilir → max_bytes 40 MB). Konum başına en yeni ölçüm; iç mekân sensörleri atlanır.
P2 = PM2.5, P1 = PM10 (µg/m³); p.rank = PM2.5."""
from . import num, ok_coord, safe_id, clean
from .. import config
from ._quake import iso_ts
from ..fetch import FetchError

META = {'mode': 'global', 'ttl': 300, 'rate_per_min': 1, 'hosts': ('data.sensor.community',), 'kind': 'airquality', 'needs_key': False,
        'refresh_s': 300}


async def fetch(ctx, src, q):
    d = await ctx.get_json('https://data.sensor.community/static/v2/data.dust.min.json', max_bytes=config.FETCH_BIG_MAX_BYTES)
    if not isinstance(d, list):
        raise FetchError('sensor_community: beklenmeyen biçim')
    best = {}
    for r in d:
        if not isinstance(r, dict):
            continue
        loc = r.get('location') or {}
        if str(loc.get('indoor')) == '1':
            continue
        lat, lon = num(loc.get('latitude')), num(loc.get('longitude'))
        lid = safe_id(loc.get('id'))
        if not ok_coord(lat, lon) or not lid:
            continue
        vals = {x.get('value_type'): num(x.get('value')) for x in r.get('sensordatavalues') or [] if isinstance(x, dict)}
        p25, p10 = vals.get('P2'), vals.get('P1')
        if p25 is None or not 0 <= p25 < 1000:
            continue
        t = iso_ts(str(r.get('timestamp') or '').replace(' ', 'T'))
        if lid in best and (best[lid]['t'] or 0) >= (t or 0):
            continue
        st = ((r.get('sensor') or {}).get('sensor_type') or {}).get('name')
        best[lid] = {'id': lid, 'lat': lat, 'lon': lon, 'name': f'PM2.5 {p25:g}', 't': t,
                     'p': clean({'pm25': p25, 'pm10': p10 if p10 is not None and 0 <= p10 < 2000 else None, 'rank': p25,
                                 'sensor': str(st)[:20] if st else None, 'country': str(loc.get('country') or '')[:2] or None})}
    return {'items': list(best.values())}
