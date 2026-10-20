"""NOAA SWPC OVATION — 30–90 dk'lık kutup ışığı olasılık ızgarası (1°; kamu malı). Olasılığı ≥ 10 olan hücreler,
p.rank = olasılık (%), en olası ≤ 4000 hücre."""
from . import num, clean
from ._quake import iso_ts
from ..fetch import FetchError

META = {'mode': 'global', 'ttl': 300, 'rate_per_min': 2, 'hosts': ('services.swpc.noaa.gov',), 'kind': 'aurora', 'needs_key': False,
        'refresh_s': 300}
MIN_PROB = 10
CAP = 4000


async def fetch(ctx, src, q):
    d = await ctx.get_json('https://services.swpc.noaa.gov/json/ovation_aurora_latest.json')
    if not isinstance(d, dict) or not isinstance(d.get('coordinates'), list):
        raise FetchError('swpc_aurora: beklenmeyen biçim')
    t = iso_ts(d.get('Forecast Time')) or iso_ts(d.get('Observation Time'))
    cells = []
    for c in d['coordinates']:
        if not isinstance(c, list) or len(c) < 3:
            continue
        lon, lat, pr = num(c[0]), num(c[1]), num(c[2])
        if lon is None or lat is None or pr is None or pr < MIN_PROB or not -90 <= lat <= 90:
            continue
        lon = lon - 360 if lon > 180 else lon
        if not -180 <= lon <= 180:
            continue
        cells.append((pr, lat, lon))
    cells.sort(key=lambda x: -x[0])
    out = [{'id': f'{lon:g},{lat:g}', 'lat': lat, 'lon': lon, 'name': f'Aurora %{pr:g}', 't': t,
            'p': clean({'prob': pr, 'rank': pr})} for pr, lat, lon in cells[:CAP]]
    return {'items': out}
