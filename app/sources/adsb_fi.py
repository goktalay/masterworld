"""adsb.fi — ADS-B uçak konumları (açık veri; ticari olmayan kullanım). Uç: /api/v2/lat/{lat}/lon/{lon}/dist/{nm} (≤ 250 nm).
Kaynağın sınırı 1 istek/sn → dakikada 50 (pay bırakılır); hücre önbelleği tüm kullanıcılar arasında paylaşılır."""
from .adsb_lol import ac_items

META = {'mode': 'bbox', 'ttl': 10, 'rate_per_min': 50, 'hosts': ('opendata.adsb.fi',), 'kind': 'aircraft', 'needs_key': False,
        'refresh_s': 10, 'cell_deg': 5, 'max_cells': 9}


async def fetch(ctx, src, q):
    d = await ctx.get_json(f"https://opendata.adsb.fi/api/v2/lat/{q['lat']:.3f}/lon/{q['lon']:.3f}/dist/{int(q['radius_nm'])}")
    return {'items': ac_items(d)}
