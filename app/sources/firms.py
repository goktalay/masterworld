"""NASA FIRMS — aktif yangın / ısıl anomali noktaları (VIIRS / MODIS NRT). Anahtar: MAP_KEY (src.api_key; ücretsiz,
5000 işlem / 10 dk). Uç: /api/area/csv/{key}/{kaynak}/world/1 — büyük CSV (≤ 40 MB). En fazla 20000 nokta, p.rank = frp."""
import csv
import io
import re

from . import clip, num, ok_coord, clean
from .. import config
from ..fetch import FetchError

META = {'mode': 'global', 'ttl': 1800, 'rate_per_min': 1, 'hosts': ('firms.modaps.eosdis.nasa.gov',), 'kind': 'fire', 'needs_key': True,
        'refresh_s': 1800}
SOURCES = {'VIIRS_SNPP_NRT', 'VIIRS_NOAA20_NRT', 'VIIRS_NOAA21_NRT', 'MODIS_NRT'}
KEY_RE = re.compile(r'^[A-Za-z0-9]{8,64}$')
MAX_POINTS = 20000


def parse(text):
    rd = csv.DictReader(io.StringIO(text))
    if not rd.fieldnames or 'latitude' not in rd.fieldnames or 'longitude' not in rd.fieldnames:
        raise FetchError('firms: CSV başlığı yok (anahtar geçersiz ya da kota)')
    out = []
    for r in rd:
        lat, lon = num(r.get('latitude')), num(r.get('longitude'))
        if not ok_coord(lat, lon):
            continue
        tm = str(r.get('acq_time') or '').zfill(4)[:4]
        date = clip(r.get('acq_date'), 10)
        frp = num(r.get('frp'))
        out.append({'id': f'{lat:.4f},{lon:.4f},{(date or "").replace("-", "")}{tm}', 'lat': lat, 'lon': lon, 'name': 'Yangın',
                    'p': clean({'frp': frp, 'rank': frp, 'conf': clip(r.get('confidence'), 8), 'sat': clip(r.get('satellite'), 8),
                                'date': date, 'time': f'{tm[:2]}:{tm[2:]}' if tm.isdigit() else None, 'dn': clip(r.get('daynight'), 1),
                                'bright': num(r.get('bright_ti4'), num(r.get('brightness')))})})
    out.sort(key=lambda it: -(it['p'].get('frp') or 0))
    return out[:MAX_POINTS]


async def fetch(ctx, src, q):
    key = str(src.get('api_key') or ctx.api_key or '')
    if not KEY_RE.match(key):
        raise FetchError('firms: MAP_KEY yok / biçimsiz')
    s = (src.get('params') or {}).get('source', 'VIIRS_SNPP_NRT')
    s = s if s in SOURCES else 'VIIRS_SNPP_NRT'
    text = await ctx.get_text(f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{s}/world/1', max_bytes=config.FETCH_BIG_MAX_BYTES)
    return {'items': parse(text)}
