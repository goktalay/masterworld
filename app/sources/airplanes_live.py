"""airplanes.live — ADS-B uçak konumları (ticari olmayan; erişim için airplanes.live ile iletişim gerekebilir: DEV'den 403).
Uç: /v2/point/{lat}/{lon}/{nm} (≤ 250 nm); kaynak sınırı 1 istek/sn."""
from .adsb_lol import ac_items

META = {'mode': 'bbox', 'ttl': 10, 'rate_per_min': 40, 'hosts': ('api.airplanes.live',), 'kind': 'aircraft', 'needs_key': False,
        'refresh_s': 10, 'cell_deg': 5, 'max_cells': 9}


async def fetch(ctx, src, q):
    d = await ctx.get_json(f"https://api.airplanes.live/v2/point/{q['lat']:.3f}/{q['lon']:.3f}/{int(q['radius_nm'])}")
    return {'items': ac_items(d)}
