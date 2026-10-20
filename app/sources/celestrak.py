"""CelesTrak — GP (OMM) yörünge öğeleri, JSON (FORMAT=json). params.groups: ['stations', 'visual', 'gps-ops', …] (≤ 6 grup).
Uydu konumu İSTEMCİDE yörüngeden yeniden hesaplanır (p.omm); sunucu yalnız ilk konumu kaba iki cisim Kepler çözümüyle
(J2 / sürüklenme yok; doğruluk ± birkaç yüz km) getirme anı için verir. CelesTrak veriyi ~2 saatte bir günceller ve sık indirmeyi
engeller → ttl 6 saat (gerçek trafik grup sayısı / 6 saat); rate_per_min 12 yalnız grupların art arda alınabilmesi için."""
import math
import re
import time
from datetime import datetime, timezone

from . import clip, num, ok_coord, clean, paced
from ..fetch import FetchError

META = {'burst': 4, 'mode': 'global', 'ttl': 6 * 3600, 'rate_per_min': 12, 'hosts': ('celestrak.org',), 'kind': 'satellite', 'needs_key': False,
        'refresh_s': 3600}
GROUP_RE = re.compile(r'^[a-z0-9-]{1,30}$')
DEFAULT_GROUPS = ('stations', 'visual')
MAX_PER_GROUP = 3000
MU = 398600.4418          # km³/s²
RE_KM = 6378.137
OMEGA_E = 7.2921150e-5    # rad/s
OMM_KEYS = ('MEAN_MOTION', 'ECCENTRICITY', 'INCLINATION', 'RA_OF_ASC_NODE', 'ARG_OF_PERICENTER', 'MEAN_ANOMALY', 'EPOCH', 'BSTAR',
            'NORAD_CAT_ID', 'OBJECT_NAME')


def epoch_ts(s):
    try:
        dt = datetime.fromisoformat(str(s).replace('Z', ''))
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc).timestamp()


def gmst(ts):
    """Greenwich ortalama yıldız zamanı (rad), IAU 1982 yaklaşığı."""
    d = ts / 86400.0 + 2440587.5 - 2451545.0
    return math.radians((280.46061837 + 360.98564736629 * d) % 360.0)


def kepler_subpoint(omm, ts):
    """İki cisim Kepler yayılımı → (lat, lon, alt_km) ya da None. Saf python; J2 yok."""
    n_rev = num(omm.get('MEAN_MOTION'))
    e = num(omm.get('ECCENTRICITY'))
    inc, raan, argp, m0 = (num(omm.get(k)) for k in ('INCLINATION', 'RA_OF_ASC_NODE', 'ARG_OF_PERICENTER', 'MEAN_ANOMALY'))
    t0 = epoch_ts(omm.get('EPOCH'))
    if None in (n_rev, e, inc, raan, argp, m0, t0) or n_rev <= 0 or not 0 <= e < 1:
        return None
    n = n_rev * 2 * math.pi / 86400.0                      # rad/s
    a = (MU / n ** 2) ** (1 / 3)
    m = (math.radians(m0) + n * (ts - t0)) % (2 * math.pi)
    ea = m if e < 0.8 else math.pi
    for _ in range(30):                                    # Newton: E − e·sinE = M
        d = (ea - e * math.sin(ea) - m) / (1 - e * math.cos(ea))
        ea -= d
        if abs(d) < 1e-10:
            break
    nu = 2 * math.atan2(math.sqrt(1 + e) * math.sin(ea / 2), math.sqrt(1 - e) * math.cos(ea / 2))
    r = a * (1 - e * math.cos(ea))
    i, o, w = math.radians(inc), math.radians(raan), math.radians(argp)
    u = w + nu
    x = r * (math.cos(o) * math.cos(u) - math.sin(o) * math.sin(u) * math.cos(i))
    y = r * (math.sin(o) * math.cos(u) + math.cos(o) * math.sin(u) * math.cos(i))
    z = r * math.sin(u) * math.sin(i)
    lon = math.degrees(math.atan2(y, x) - gmst(ts))
    lon = (lon + 540) % 360 - 180
    lat = math.degrees(math.atan2(z, math.hypot(x, y)))
    return lat, lon, r - RE_KM


def items(rows, ts, seen):
    out = []
    for o in rows[:MAX_PER_GROUP]:
        if not isinstance(o, dict):
            continue
        norad = num(o.get('NORAD_CAT_ID'))
        if norad is None or int(norad) in seen:
            continue
        pos = kepler_subpoint(o, ts)
        if not pos:
            continue
        lat, lon, alt = pos
        if not ok_coord(lat, lon):
            continue
        seen.add(int(norad))
        omm = clean({k: (clip(o.get(k), 40) if k in ('EPOCH', 'OBJECT_NAME') else num(o.get(k))) for k in OMM_KEYS})
        name = clip(o.get('OBJECT_NAME'), 40) or str(int(norad))
        out.append({'id': str(int(norad)), 'lat': round(lat, 4), 'lon': round(lon, 4), 'alt': round(alt * 1000), 'name': name,
                    't': int(ts), 'p': clean({'norad': int(norad), 'intl': clip(o.get('OBJECT_ID'), 16), 'alt_km': round(alt),
                                              'period_min': round(1440 / omm['MEAN_MOTION'], 1) if omm.get('MEAN_MOTION') else None,
                                              'omm': omm})})
    return out


async def fetch(ctx, src, q):
    groups = (src.get('params') or {}).get('groups') or DEFAULT_GROUPS
    if isinstance(groups, str):
        groups = [g.strip() for g in groups.split(',')]
    groups = [g for g in groups if isinstance(g, str) and GROUP_RE.match(g)][:6] or list(DEFAULT_GROUPS)
    ts, seen, out, ok = time.time(), set(), [], 0
    for g in groups:
        try:
            rows = await paced(ctx, lambda g=g: ctx.get_json(f'https://celestrak.org/NORAD/elements/gp.php?GROUP={g}&FORMAT=json'))
        except FetchError:
            continue
        if not isinstance(rows, list):
            continue
        ok += 1
        for it in items(rows, ts, seen):
            it['p']['group'] = g
            out.append(it)
    if not ok:
        raise FetchError('celestrak: hiçbir grup alınamadı')
    return {'items': out}
