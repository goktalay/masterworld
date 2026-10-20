"""NOAA Aviation Weather Center — METAR gözlemleri (kamu malı). bbox sırası: güney,batı,kuzey,doğu (lat0,lon0,lat1,lon1).
10°'lik hücreler, hücre önbelleği paylaşılır; AWC sınırı 100 istek/dk → dakikada en çok 30."""
from . import clip, num, ok_coord, safe_id, clean
from ..fetch import FetchError

META = {'mode': 'bbox', 'ttl': 600, 'rate_per_min': 30, 'hosts': ('aviationweather.gov',), 'kind': 'metar', 'needs_key': False,
        'refresh_s': 600, 'cell_deg': 10, 'max_cells': 9}


def items(d):
    if not isinstance(d, list):
        raise FetchError('metar: beklenmeyen biçim')
    out = []
    for m in d:
        if not isinstance(m, dict):
            continue
        lat, lon = num(m.get('lat')), num(m.get('lon'))
        icao = safe_id(clip(m.get('icaoId'), 8))
        if not ok_coord(lat, lon) or not icao:
            continue
        wdir, wspd, gust = m.get('wdir'), num(m.get('wspd')), num(m.get('wgst'))
        wd = 'VRB' if wdir == 'VRB' else (f'{int(num(wdir)):03d}°' if num(wdir) is not None else None)
        wind = f'{wd} {wspd:g} kt' + (f' G{gust:g}' if gust else '') if wd and wspd is not None else None
        vis = m.get('visib')
        out.append({'id': icao, 'lat': lat, 'lon': lon, 'name': icao, 't': int(num(m.get('obsTime'), 0)) or None,
                    'p': clean({'raw': clip(m.get('rawOb'), 240), 'temp': num(m.get('temp')), 'dewp': num(m.get('dewp')), 'wind': wind,
                                'vis': clip(vis, 8) if vis is not None else None, 'altim': num(m.get('altim')),
                                'flt_cat': clip(m.get('fltCat'), 4), 'site': clip(m.get('name'), 80)})})
    return out


async def fetch(ctx, src, q):
    w, s, e, n = q['cell']
    d = await ctx.get_json(f'https://aviationweather.gov/api/data/metar?bbox={s:g},{w:g},{min(n, 90):g},{min(e, 180):g}&format=json')
    return {'items': items(d)}
