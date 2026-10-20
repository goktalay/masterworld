"""adsb.lol — ADS-B uçak konumları (ODbL). Küresel anlık görüntü ucu yok: nokta + yarıçap (≤ 250 nm) sorgusu, sunucu
görünüm alanını 5°'lik hücrelere böler; hücre önbelleği tüm kullanıcılar arasında paylaşılır."""
from . import clip, num, ok_coord

META = {'burst': 18, 'mode': 'bbox', 'ttl': 10, 'rate_per_min': 120, 'hosts': ('api.adsb.lol',), 'kind': 'aircraft', 'needs_key': False,
        'refresh_s': 10, 'cell_deg': 5, 'max_cells': 9}
BASE = 'https://api.adsb.lol/v2'


def ac_items(d):
    """ADSBExchange v2 şeması (adsb.lol / adsb.fi / airplanes.live ortak) → öğeler."""
    out = []
    for a in (d or {}).get('ac') or (d or {}).get('aircraft') or []:
        lat, lon = num(a.get('lat')), num(a.get('lon'))
        if not ok_coord(lat, lon):
            continue
        alt = a.get('alt_baro')
        on_ground = alt == 'ground'
        alt_ft = None if on_ground else num(alt, num(a.get('alt_geom')))
        hexid = clip(a.get('hex'), 12) or ''
        out.append({'id': hexid or f'{lat:.4f},{lon:.4f}', 'lat': lat, 'lon': lon,
                    'alt': round(alt_ft * 0.3048) if alt_ft is not None else None,
                    'hdg': num(a.get('track'), num(a.get('true_heading'))), 'spd': num(a.get('gs')),
                    'name': clip(a.get('flight'), 12) or clip(a.get('r'), 12) or hexid.upper(),
                    'p': {k: v for k, v in {'hex': hexid, 'reg': clip(a.get('r'), 16), 'type': clip(a.get('t'), 10),
                                            'desc': clip(a.get('desc'), 60), 'squawk': clip(a.get('squawk'), 6),
                                            'alt_ft': alt_ft, 'ground': on_ground or None, 'gs_kt': num(a.get('gs')),
                                            'vs_fpm': num(a.get('baro_rate')), 'cat': clip(a.get('category'), 4),
                                            'mil': bool(a.get('dbFlags', 0) & 1) or None, 'op': clip(a.get('ownOp'), 60)}.items() if v is not None}})
    return out


async def fetch(ctx, src, q):
    d = await ctx.get_json(f"{BASE}/point/{q['lat']:.3f}/{q['lon']:.3f}/{int(q['radius_nm'])}")
    return {'items': ac_items(d)}
