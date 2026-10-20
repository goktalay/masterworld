"""SondeHub — radyosonde (meteoroloji balonu) son konumları, son 1 saat (CC BY-SA 4.0). Uç: /sondes?last=3600 (seri no → son kayıt)."""
from . import clip, num, ok_coord, safe_id, clean
from ._quake import iso_ts
from ..fetch import FetchError

META = {'mode': 'global', 'ttl': 30, 'rate_per_min': 4, 'hosts': ('api.v2.sondehub.org',), 'kind': 'sonde', 'needs_key': False,
        'refresh_s': 30}


async def fetch(ctx, src, q):
    d = await ctx.get_json('https://api.v2.sondehub.org/sondes?last=3600')
    if not isinstance(d, dict):
        raise FetchError('sondehub: beklenmeyen biçim')
    out = []
    for serial, s in list(d.items())[:5000]:
        if not isinstance(s, dict):
            continue
        lat, lon = num(s.get('lat')), num(s.get('lon'))
        sid = safe_id(s.get('serial') or serial, 40)
        if not ok_coord(lat, lon) or not sid:
            continue
        alt = num(s.get('alt'))
        out.append({'id': sid, 'lat': lat, 'lon': lon, 'alt': round(alt) if alt is not None else None, 'name': sid,
                    'hdg': num(s.get('heading')), 'spd': round(num(s.get('vel_h')) * 1.943844, 1) if num(s.get('vel_h')) is not None else None,
                    't': iso_ts(s.get('datetime')),
                    'p': clean({'alt': round(alt) if alt is not None else None, 'type': clip(s.get('subtype') or s.get('type'), 20),
                                'frame': int(num(s.get('frame'))) if num(s.get('frame')) is not None else None,
                                'vel_v': num(s.get('vel_v')), 'temp': num(s.get('temp')), 'freq': num(s.get('tx_frequency')),
                                'uploader': clip(s.get('uploader_callsign'), 20),
                                'url': f'https://sondehub.org/{sid}'})})
    return {'items': out}
