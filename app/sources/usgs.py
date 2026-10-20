"""USGS Earthquake Hazards — GeoJSON özet beslemeleri (kamu malı). params.feed: all_hour | all_day | 2.5_day | 4.5_week | significant_month."""
from . import clip, num, ok_coord

META = {'mode': 'global', 'ttl': 60, 'rate_per_min': 6, 'hosts': ('earthquake.usgs.gov',), 'kind': 'quake', 'needs_key': False, 'refresh_s': 60}
FEEDS = {'all_hour', 'all_day', '1.0_day', '2.5_day', '4.5_day', 'significant_day', 'all_week', '2.5_week', '4.5_week',
         'significant_week', '4.5_month', 'significant_month'}


async def fetch(ctx, src, q):
    feed = src.get('params', {}).get('feed', 'all_day')
    feed = feed if feed in FEEDS else 'all_day'
    d = await ctx.get_json(f'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{feed}.geojson')
    out = []
    for f in d.get('features') or []:
        g = (f.get('geometry') or {}).get('coordinates') or []
        p = f.get('properties') or {}
        lon, lat = (num(g[0]), num(g[1])) if len(g) >= 2 else (None, None)
        if not ok_coord(lat, lon):
            continue
        mag = num(p.get('mag'))
        out.append({'id': clip(f.get('id'), 40), 'lat': lat, 'lon': lon, 'name': clip(p.get('place'), 120) or 'Deprem',
                    't': int(num(p.get('time'), 0) / 1000) or None,
                    'p': {k: v for k, v in {'mag': mag, 'depth_km': num(g[2]) if len(g) > 2 else None, 'type': clip(p.get('magType'), 6),
                                            'tsunami': 1 if p.get('tsunami') else None, 'alert': clip(p.get('alert'), 10),
                                            'felt': p.get('felt'), 'url': clip(p.get('url'), 200)}.items() if v is not None}})
    return {'items': out}
