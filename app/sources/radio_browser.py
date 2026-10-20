"""Radio Browser — topluluk radyo istasyonları dizini (kamu malı / açık). Konumlu, çalışan, en çok oy alan ≤ 20000 istasyon,
YALNIZ https akışlar (is_https=true sunucuda süzülür; url_resolved yine denetlenir). Ses tarayıcıda doğrudan çalar (p.stream).
Sunucular DNS çevrimli (all.api.radio-browser.info/json/servers); beyaz listede bilinenler var, params.host ile seçilebilir,
yoksa her yenilemede sırayla denenir. Yanıt ~14 MB → max_bytes 40 MB; ttl 12 saat."""
import itertools

from . import clip, num, ok_coord, safe_id, clean
from .. import config
from ..fetch import FetchError

SERVERS = ('de1.api.radio-browser.info', 'de2.api.radio-browser.info', 'fi1.api.radio-browser.info', 'nl1.api.radio-browser.info',
           'at1.api.radio-browser.info', 'all.api.radio-browser.info')
META = {'mode': 'global', 'ttl': 12 * 3600, 'rate_per_min': 2, 'hosts': SERVERS, 'kind': 'radio', 'needs_key': False, 'refresh_s': 3600}
_rot = itertools.cycle(SERVERS[:5])


def items(d):
    if not isinstance(d, list):
        raise FetchError('radio_browser: beklenmeyen biçim')
    out = []
    for s in d:
        if not isinstance(s, dict):
            continue
        url = str(s.get('url_resolved') or '')
        lat, lon = num(s.get('geo_lat')), num(s.get('geo_long'))
        sid = safe_id(s.get('stationuuid'))
        if not url.startswith('https://') or len(url) > 400 or not ok_coord(lat, lon) or not sid:
            continue
        fav, home = str(s.get('favicon') or ''), str(s.get('homepage') or '')
        tags = [t.strip()[:24] for t in str(s.get('tags') or '').split(',') if t.strip()][:5]
        votes = int(num(s.get('votes'), 0))
        out.append({'id': sid, 'lat': lat, 'lon': lon, 'name': clip(s.get('name'), 100) or 'Radyo',
                    'p': clean({'stream': url, 'codec': clip(s.get('codec'), 12), 'bitrate': int(num(s.get('bitrate'), 0)) or None,
                                'country': clip(s.get('country'), 60), 'countrycode': clip(s.get('countrycode'), 2),
                                'tags': tags or None, 'homepage': clip(home, 200) if home.startswith(('https://', 'http://')) else None,
                                'favicon': clip(fav, 300) if fav.startswith('https://') else None,
                                'votes': votes, 'rank': votes, 'is_hls': True if s.get('hls') else None})})
    return out


async def fetch(ctx, src, q):
    host = (src.get('params') or {}).get('host')
    host = host if host in SERVERS else next(_rot)
    d = await ctx.get_json(f'https://{host}/json/stations/search?has_geo_info=true&hidebroken=true&is_https=true&order=votes&reverse=true'
                           '&limit=20000', max_bytes=config.FETCH_BIG_MAX_BYTES)
    return {'items': items(d)}
