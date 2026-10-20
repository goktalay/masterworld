"""Windy Webcams API v3 — dünya web kameraları (anahtar: x-windy-api-key = src.api_key; atıf ZORUNLU: "Webcams provided by
windy.com" + kamera sayfası bağlantısı p.url). bbox biçimi: kuzey,doğu,güney,batı; limit ≤ 50. Ücretsiz katmanda görüntü
adreslerindeki belirteç 10 dk'da düşer → ttl 300 (adres her yenilemede tazelenir)."""
from . import clip, num, ok_coord, safe_id, clean
from ..fetch import FetchError

META = {'mode': 'bbox', 'ttl': 300, 'rate_per_min': 10, 'hosts': ('api.windy.com',), 'kind': 'camera', 'needs_key': True,
        'refresh_s': 300, 'cell_deg': 10, 'max_cells': 4}
MEDIA_HOSTS = ('imgproxy.windy.com', 'images-webcams.windy.com')


def items(d):
    if not isinstance(d, dict) or not isinstance(d.get('webcams'), list):
        raise FetchError('windy_webcams: beklenmeyen biçim')
    out = []
    for w in d['webcams']:
        if not isinstance(w, dict) or w.get('status', 'active') != 'active':
            continue
        loc = w.get('location') or {}
        lat, lon = num(loc.get('latitude')), num(loc.get('longitude'))
        wid = safe_id(w.get('webcamId'))
        if not ok_coord(lat, lon) or not wid:
            continue
        img = str((((w.get('images') or {}).get('current') or {}).get('preview')) or '')
        url = str((w.get('urls') or {}).get('detail') or '')
        it = {'id': wid, 'lat': lat, 'lon': lon, 'name': clip(w.get('title'), 120) or 'Webcam',
              'p': clean({'city': clip(loc.get('city'), 60), 'country': clip(loc.get('country'), 60), 'views': num(w.get('viewCount')),
                          'rank': num(w.get('viewCount')), 'updated': clip(w.get('lastUpdatedOn'), 24),
                          'url': clip(url, 200) if url.startswith('https://') else f'https://www.windy.com/webcams/{wid}',
                          'credit': 'Webcams provided by windy.com'})}
        if img.startswith('https://'):
            it['_media'] = img
        out.append(it)
    return out


async def fetch(ctx, src, q):
    key = str(src.get('api_key') or ctx.api_key or '')
    if not key:
        raise FetchError('windy_webcams: anahtar yok')
    w, s, e, n = q['cell']
    d = await ctx.get_json(f'https://api.windy.com/webcams/api/v3/webcams?lang=en&limit=50&offset=0&sortKey=popularity&sortDirection=desc'
                           f'&bbox={min(n, 90):g},{min(e, 180):g},{s:g},{w:g}&include=images,location,urls',
                           headers={'x-windy-api-key': key})
    return {'items': items(d)}
