"""Where the ISS at? — ISS anlık konumu (api.wheretheiss.at; kaynak sınırı ~1 istek/sn). Tek öğe, kind iss."""
from . import num, ok_coord, clean
from ..fetch import FetchError

META = {'mode': 'global', 'ttl': 5, 'rate_per_min': 20, 'hosts': ('api.wheretheiss.at',), 'kind': 'iss', 'needs_key': False, 'refresh_s': 5}


async def fetch(ctx, src, q):
    d = await ctx.get_json('https://api.wheretheiss.at/v1/satellites/25544')
    if not isinstance(d, dict):
        raise FetchError('wheretheiss: beklenmeyen biçim')
    lat, lon = num(d.get('latitude')), num(d.get('longitude'))
    if not ok_coord(lat, lon):
        raise FetchError('wheretheiss: konum yok')
    alt, vel = num(d.get('altitude')), num(d.get('velocity'))
    vis = d.get('visibility') if d.get('visibility') in ('daylight', 'eclipsed', 'visible') else None
    return {'items': [{'id': '25544', 'lat': round(lat, 4), 'lon': round(lon, 4), 'alt': round(alt * 1000) if alt is not None else None,
                       'name': 'ISS', 't': int(num(d.get('timestamp'), 0)) or None,
                       'p': clean({'alt_km': round(alt, 1) if alt is not None else None, 'vel_kmh': round(vel) if vel is not None else None,
                                   'visibility': vis, 'footprint_km': round(num(d.get('footprint'), 0)) or None})}]}
