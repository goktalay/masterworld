"""NOAA NDBC — etkin şamandıra / istasyon listesi (activestations.xml) + tüm istasyonların son gözlemi (latest_obs.txt, tek dosya).
Kamu malı. XML ayrıştırıcı kullanılmaz (dış kaynak): <station …/> öznitelikleri düzenli ifadeyle okunur."""
import html
import re
from datetime import datetime, timezone

from . import clip, num, ok_coord, safe_id, clean, paced
from ..fetch import FetchError

META = {'burst': 2, 'mode': 'global', 'ttl': 900, 'rate_per_min': 12, 'hosts': ('www.ndbc.noaa.gov',), 'kind': 'buoy', 'needs_key': False,
        'refresh_s': 900}
ST_RE = re.compile(r'<station\s([^>]*?)/?>')
AT_RE = re.compile(r'([a-z_]+)="([^"]*)"')
OBS_KEYS = {'WDIR': 'wdir', 'WSPD': 'wspd', 'GST': 'gst', 'WVHT': 'wvht', 'DPD': 'dpd', 'PRES': 'pres', 'ATMP': 'atmp', 'WTMP': 'wtmp',
            'DEWP': 'dewp', 'VIS': 'vis'}


def stations(xml):
    if '<stations' not in xml[:2000]:
        raise FetchError('ndbc: istasyon listesi beklenmeyen biçimde')
    out = {}
    for m in ST_RE.finditer(xml):
        a = {k: html.unescape(v) for k, v in AT_RE.findall(m.group(1))}
        sid = safe_id(a.get('id'), 12)
        if sid:
            out[sid.upper()] = a
    return out


def observations(txt):
    lines = txt.splitlines()
    if not lines or not lines[0].startswith('#STN'):
        raise FetchError('ndbc: gözlem dosyası beklenmeyen biçimde')
    hdr = lines[0].lstrip('#').split()
    obs = {}
    for ln in lines[2:]:
        f = ln.split()
        if len(f) != len(hdr):
            continue
        r = dict(zip(hdr, f))
        sid = safe_id(r.get('STN'), 12)
        if not sid:
            continue
        try:
            t = int(datetime(int(r['YYYY']), int(r['MM']), int(r['DD']), int(r['hh']), int(r['mm']), tzinfo=timezone.utc).timestamp())
        except (KeyError, ValueError):
            t = None
        o = {v: num(r.get(k)) for k, v in OBS_KEYS.items() if r.get(k) not in (None, 'MM')}
        obs[sid.upper()] = (t, clean(o), num(r.get('LAT')), num(r.get('LON')))
    return obs


async def fetch(ctx, src, q):
    st = stations(await ctx.get_text('https://www.ndbc.noaa.gov/activestations.xml'))
    obs = observations(await paced(ctx, lambda: ctx.get_text('https://www.ndbc.noaa.gov/data/latest_obs/latest_obs.txt')))
    out = []
    for sid, a in st.items():
        t, o, olat, olon = obs.get(sid, (None, {}, None, None))
        lat, lon = num(a.get('lat'), olat), num(a.get('lon'), olon)
        if not ok_coord(lat, lon):
            continue
        out.append({'id': sid, 'lat': lat, 'lon': lon, 'name': clip(a.get('name'), 80) or sid, 't': t,
                    'p': clean({'station': sid, 'type': clip(a.get('type'), 16), 'owner': clip(a.get('owner'), 80), 'rank': 1 if o else None,
                                'url': f'https://www.ndbc.noaa.gov/station_page.php?station={sid.lower()}'} | o)})
    return {'items': out}
