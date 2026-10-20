"""Open-Meteo — tıklanan nokta için anlık hava + 24 saatlik saatlik tahmin (CC BY 4.0; ticari olmayan ücretsiz katman).
Dönüş: tek öğe (anlık özet) + 'data' (engine point modunda istemciye iletir): {current, hourly, units}."""
from . import num, clean
from ..fetch import FetchError

META = {'mode': 'point', 'ttl': 900, 'rate_per_min': 30, 'hosts': ('api.open-meteo.com',), 'kind': 'forecast', 'needs_key': False,
        'refresh_s': 900}
VARS = ('temperature_2m', 'wind_speed_10m', 'wind_direction_10m', 'weather_code', 'precipitation', 'relative_humidity_2m')


async def fetch(ctx, src, q):
    lat, lon = num(q.get('lat')), num(q.get('lon'))
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise FetchError('open_meteo: koordinat geçersiz')
    v = ','.join(VARS)
    d = await ctx.get_json(f'https://api.open-meteo.com/v1/forecast?latitude={lat:.2f}&longitude={lon:.2f}&current={v}&hourly={v}'
                           '&forecast_hours=24&timezone=UTC&wind_speed_unit=kmh')
    if not isinstance(d, dict) or not isinstance(d.get('current'), dict):
        raise FetchError('open_meteo: beklenmeyen biçim')
    cur = {k: num(d['current'].get(k)) for k in VARS}
    hr = d.get('hourly') or {}
    hourly = {'time': [str(t)[:16] for t in (hr.get('time') or [])[:24]]}
    for k in VARS:
        hourly[k] = [num(x) for x in (hr.get(k) or [])[:24]]
    units = {k: str(u)[:8] for k, u in (d.get('current_units') or {}).items() if k in VARS}
    data = {'current': clean(cur) | {'time': str(d['current'].get('time') or '')[:16]}, 'hourly': hourly, 'units': units,
            'elevation': num(d.get('elevation'))}
    t = cur.get('temperature_2m')
    item = {'id': f'{lat:.1f},{lon:.1f}', 'lat': lat, 'lon': lon,
            'name': f'{t:g} °C' if t is not None else 'Hava', 'p': clean({'temp': t, 'wind_kmh': cur.get('wind_speed_10m'),
                                                                         'wind_dir': cur.get('wind_direction_10m'), 'code': cur.get('weather_code'),
                                                                         'precip_mm': cur.get('precipitation'), 'rh': cur.get('relative_humidity_2m')})}
    return {'items': [item], 'data': data}
