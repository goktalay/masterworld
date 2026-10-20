"""RainViewer — küresel yağış radarı karoları (ücretsiz genel API: z ≤ 7 — z 8'de "Zoom Level Not Supported" görüntüsü döner,
renk şeması 2, yumuşatma 1; atıf "RainViewer"). Harita listesi weather-maps.json 5 dk önbellekte; en son radar karesi."""
import re

from .. import fetch as _fetch
from ..fetch import FetchError

META = {'mode': 'tile', 'ttl': 300, 'rate_per_min': 300, 'hosts': ('api.rainviewer.com', 'tilecache.rainviewer.com'), 'kind': 'radar',
        'needs_key': False, 'refresh_s': 300, 'max_zoom': 7}
PATH_RE = re.compile(r'^/v2/radar/[A-Za-z0-9_-]{4,40}$')
TILE_HOST = 'https://tilecache.rainviewer.com'


async def latest(ctx):
    async def get():
        d = await ctx.get_json('https://api.rainviewer.com/public/weather-maps.json')
        past = ((d or {}).get('radar') or {}).get('past') if isinstance(d, dict) else None
        if not past or not isinstance(past, list):
            raise FetchError('rainviewer: radar listesi yok')
        last = past[-1] if isinstance(past[-1], dict) else {}
        path = str(last.get('path') or '')
        if not PATH_RE.match(path) or str(d.get('host') or TILE_HOST).rstrip('/') != TILE_HOST:
            raise FetchError('rainviewer: beklenmeyen yol / host')
        return {'path': path, 'time': int(last.get('time') or 0)}
    val, _ = await _fetch.cached(f'rv:maps:{ctx.slug}', 300, get, stale=1800)
    return val


async def tile_url(ctx, src, z, x, y):
    m = await latest(ctx)
    return f"{TILE_HOST}{m['path']}/256/{int(z)}/{int(x)}/{int(y)}/2/1_1.png"
