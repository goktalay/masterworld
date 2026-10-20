"""OpenSky Network — /api/states/all (bbox). Kimlik: OAuth2 client credentials (src.api_key = "client_id:client_secret"),
belirteç auth.opensky-network.org'dan; modül içinde süresinden 60 sn önceye kadar önbellekte tutulur.
Kredi bütçesi (kayıtlı hesap ~4000/gün; 25–100 kare derece alan = 2 kredi): 10°'lik hücre, dakikada ≤ 1.2 istek ≈ 1730/gün."""
import time

from . import clip, num, ok_coord, safe_id, clean
from .. import fetch as _fetch
from ..fetch import FetchError

META = {'mode': 'bbox', 'ttl': 60, 'rate_per_min': 1.2, 'hosts': ('opensky-network.org',),
        'kind': 'aircraft', 'needs_key': True, 'refresh_s': 60, 'cell_deg': 10, 'max_cells': 4}
TOKEN_URL = 'https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token'
_tok = {}   # client_id → (belirteç, bitiş)


async def _token(ctx, src):
    key = str(src.get('api_key') or ctx.api_key or '')
    cid, _, secret = key.partition(':')
    if not cid or not secret:
        raise FetchError('opensky: api_key "client_id:client_secret" biçiminde değil')
    t = _tok.get(cid)
    if t and time.time() < t[1]:
        return t[0]
    # belirteç isteği ayrı kova ve yalnız auth host'u ile (veri kovasının tek jetonunu tüketmesin)
    actx = _fetch.Ctx(f'{ctx.slug}:auth', ('auth.opensky-network.org',), 2)
    d = await actx.post_form(TOKEN_URL, {'grant_type': 'client_credentials', 'client_id': cid, 'client_secret': secret})
    tok = d.get('access_token') if isinstance(d, dict) else None
    if not tok:
        raise FetchError('opensky: belirteç alınamadı')
    _tok[cid] = (tok, time.time() + max(60, int(num(d.get('expires_in'), 1800)) - 60))
    if len(_tok) > 16:
        _tok.pop(next(iter(_tok)))
    return tok


def items(d):
    if not isinstance(d, dict) or not isinstance(d.get('states', []), (list, type(None))):
        raise FetchError('opensky: beklenmeyen biçim')
    out = []
    for s in d.get('states') or []:
        if not isinstance(s, list) or len(s) < 17:
            continue
        lon, lat = num(s[5]), num(s[6])
        if not ok_coord(lat, lon):
            continue
        icao = safe_id(clip(s[0], 12))
        if not icao:
            continue
        alt_m = num(s[13], num(s[7]))
        spd = num(s[9])
        out.append({'id': icao, 'lat': lat, 'lon': lon, 'alt': round(alt_m) if alt_m is not None and not s[8] else None,
                    'hdg': num(s[10]), 'spd': round(spd * 1.943844, 1) if spd is not None else None,
                    'name': clip(s[1], 12) or icao.upper(), 't': int(num(s[3], 0)) or None,
                    'p': clean({'hex': icao, 'country': clip(s[2], 40), 'alt_ft': round(num(s[7]) / 0.3048) if num(s[7]) is not None else None,
                                'ground': True if s[8] else None, 'vs_fpm': round(num(s[11]) * 196.85) if num(s[11]) is not None else None,
                                'squawk': clip(s[14], 6)})})
    return out


async def fetch(ctx, src, q):
    w, s, e, n = q['cell']
    tok = await _token(ctx, src)
    d = await ctx.get_json(f'https://opensky-network.org/api/states/all?lamin={s}&lomin={w}&lamax={min(n, 90)}&lomax={min(e, 180)}',
                           headers={'Authorization': f'Bearer {tok}'})
    return {'items': items(d)}
