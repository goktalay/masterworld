"""Digitraffic (Fintraffic, Finlandiya) — yol hava kameraları; açık veri CC BY 4.0 (atıf "Fintraffic / digitraffic.fi"), anahtarsız.
İstasyon listesi tie.digitraffic.fi/api/weathercam/v1/stations: sıkıştırma (Accept-Encoding: gzip) ZORUNLU (yoksa 406) — ortak istemci
zaten gönderir; ayrıca kibar kullanım için Digitraffic-User başlığı. Her istasyonun ilk (toplanan) ön ayarı → weathercam.digitraffic.fi/{id}.jpg."""
import re

from . import clip, num, ok_coord, safe_id, clean
from ..fetch import FetchError

META = {'mode': 'global', 'ttl': 600, 'rate_per_min': 6, 'hosts': ('tie.digitraffic.fi',), 'kind': 'camera', 'needs_key': False,
        'refresh_s': 600}
MEDIA_HOSTS = ('weathercam.digitraffic.fi',)
HEADERS = {'Digitraffic-User': 'MASTERWORLD/masterworld.app', 'Accept-Encoding': 'gzip'}
PRESET_RE = re.compile(r'^[A-Z0-9]{4,16}$')


async def fetch(ctx, src, q):
    d = await ctx.get_json('https://tie.digitraffic.fi/api/weathercam/v1/stations', headers=HEADERS)
    if not isinstance(d, dict) or not isinstance(d.get('features'), list):
        raise FetchError('digitraffic_cam: beklenmeyen biçim')
    out = []
    for f in d['features']:
        g = ((f or {}).get('geometry') or {}).get('coordinates') or []
        p = f.get('properties') or {}
        lon, lat = (num(g[0]), num(g[1])) if len(g) >= 2 else (None, None)
        sid = safe_id(p.get('id') or f.get('id'))
        if not ok_coord(lat, lon) or not sid or p.get('collectionStatus') not in (None, 'GATHERING'):
            continue
        presets = [x.get('id') for x in p.get('presets') or [] if isinstance(x, dict) and x.get('inCollection', True)]
        pid = next((x for x in presets if isinstance(x, str) and PRESET_RE.match(x)), None)
        if not pid:
            continue
        out.append({'id': sid, 'lat': lat, 'lon': lon, 'name': clip(str(p.get('name') or sid).replace('_', ' '), 120),
                    '_media': f'https://weathercam.digitraffic.fi/{pid}.jpg',
                    'p': clean({'preset': pid, 'presets': len(presets), 'updated': clip(p.get('dataUpdatedTime'), 24),
                                'url': 'https://www.digitraffic.fi/en/road-traffic/'})})
    return {'items': out}
