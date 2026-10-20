"""Caltrans CWWP2 — Kaliforniya DOT trafik kameraları (kamu; anahtarsız). 12 bölge dosyası d{1..12}/cctv/cctvStatusD{NN}.json.
Görüntü imageData.static.currentImageURL (vekilden; MEDIA_HOSTS), varsa canlı akış imageData.streamingVideoURL → p.hls.
Bölgelerden biri alınamazsa (oran kovası / zaman aşımı) o bölgenin son başarılı listesi kullanılır."""
import time

from . import clip, num, ok_coord, safe_id, clean, paced
from ..fetch import FetchError

META = {'burst': 12, 'mode': 'global', 'ttl': 300, 'rate_per_min': 30, 'hosts': ('cwwp2.dot.ca.gov',), 'kind': 'camera', 'needs_key': False,
        'refresh_s': 300}
MEDIA_HOSTS = ('cwwp2.dot.ca.gov',)
DISTRICTS = range(1, 13)
_last = {}   # bölge → (öğeler, zaman)


def items(d, dist):
    if not isinstance(d, dict) or not isinstance(d.get('data'), list):
        raise FetchError('caltrans_cctv: beklenmeyen biçim')
    out = []
    for row in d['data']:
        c = (row or {}).get('cctv') if isinstance(row, dict) else None
        if not isinstance(c, dict) or str(c.get('inService', 'true')).lower() != 'true':
            continue
        loc = c.get('location') or {}
        lat, lon = num(loc.get('latitude')), num(loc.get('longitude'))
        cid = safe_id(f"d{dist}-{c.get('index')}")
        if not ok_coord(lat, lon) or not cid:
            continue
        im = c.get('imageData') or {}
        img = str((im.get('static') or {}).get('currentImageURL') or '')
        hls = str(im.get('streamingVideoURL') or '')
        it = {'id': cid, 'lat': lat, 'lon': lon, 'name': clip(loc.get('locationName'), 120) or 'Caltrans CCTV',
              'p': clean({'route': clip(loc.get('route'), 20), 'county': clip(loc.get('county'), 40), 'place': clip(loc.get('nearbyPlace'), 60),
                          'dir': clip(loc.get('direction'), 12), 'district': dist,
                          'hls': clip(hls, 300) if hls.startswith('https://') and hls.endswith('.m3u8') else None})}
        if img.startswith('https://cwwp2.dot.ca.gov/'):
            it['_media'] = img
        out.append(it)
    return out


async def fetch(ctx, src, q):
    out, ok = [], 0
    for n in DISTRICTS:
        url = f'https://cwwp2.dot.ca.gov/data/d{n}/cctv/cctvStatusD{n:02d}.json'
        try:
            its = items(await paced(ctx, lambda url=url: ctx.get_json(url)), n)
            _last[n] = (its, time.time())
            ok += 1
        except FetchError:
            its = _last.get(n, ([], 0))[0] if time.time() - _last.get(n, ([], 0))[1] < 6 * 3600 else []
        out += its
    if not ok and not out:
        raise FetchError('caltrans_cctv: hiçbir bölge alınamadı')
    return {'items': out}
