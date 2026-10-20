"""Canlı duman testi (ağa ÇIKAR; MW_OFFLINE kullanılmaz): her anahtarsız adaptörü gerçek kaynağa BİR kez çağırır,
öğe / çizgi sayısını ve süreyi yazar. Kaynaklara kibar olun: elle, seyrek çalıştırın.

    cd <depo> && /opt/hepgo/fabrika-yonetim/.venv/bin/python -m tests.live_smoke [adaptör …]
"""
import asyncio
import os
import sys
import time

os.environ.pop('MW_OFFLINE', None)

from app import fetch  # noqa: E402
from app.sources import ADAPTERS, load_all  # noqa: E402

BBOX_Q = {   # adaptör → (hücre w, s, e, n) — yoğun bölgeler
    'adsb_lol': (25, 40, 30, 45), 'adsb_fi': (25, 40, 30, 45), 'airplanes_live': (25, 40, 30, 45),
    'metar': (20, 40, 30, 50), 'windy_webcams': (20, 40, 30, 50), 'opensky': (20, 40, 30, 50),
}


def q_for(name, meta):
    mode = meta.get('mode')
    if mode == 'bbox':
        w, s, e, n = BBOX_Q.get(name, (25, 40, 30, 45))
        return {'cell': (w, s, e, n), 'lat': (s + n) / 2, 'lon': (w + e) / 2, 'radius_nm': 200}
    if mode == 'point':
        return {'lat': 41.0, 'lon': 29.0}
    return {}


async def one(name, mod):
    m = mod.META
    src = {'slug': f'smoke-{name}', 'params': {}, 'api_key': None}
    ctx = fetch.Ctx(src['slug'], m.get('hosts'), m.get('rate_per_min', 30))
    t0 = time.monotonic()
    try:
        if m.get('mode') == 'tile':
            url = await mod.tile_url(ctx, src, 3, 4, 2)
            body, ctype = await ctx.get_bytes(url, max_bytes=1024 * 1024, accept='image/png')
            msg = f'karo {len(body)} B {ctype}'
        else:
            res = await mod.fetch(ctx, src, q_for(name, m))
            msg = f"{len(res.get('items') or [])} öğe" + (f", {len(res['lines'])} çizgi" if res.get('lines') else '')
            if res.get('data'):
                msg += f", data: {sorted(res['data'])}"
            media = [it for it in res.get('items') or [] if it.get('_media')]
            if media and getattr(mod, 'MEDIA_HOSTS', None):   # bir görüntüyü vekil denetimiyle dene
                mctx = fetch.Ctx(src['slug'] + ':m', mod.MEDIA_HOSTS, 10)
                try:
                    b, ct = await mctx.get_bytes(media[0]['_media'], max_bytes=2 * 1024 * 1024, accept='image/*')
                    msg += f'; görüntü {len(b)} B {ct}'
                except fetch.FetchError as e:
                    msg += f'; görüntü HATA {e}'
    except fetch.FetchError as e:
        msg = f'HATA {e}'
    except Exception as e:   # noqa: BLE001 — adaptör hatası raporlansın
        msg = f'İSTİSNA {type(e).__name__}: {e}'
    print(f'{name:18s} {time.monotonic() - t0:6.2f} sn  {msg}', flush=True)


async def main(names):
    load_all()
    for name in sorted(ADAPTERS):
        mod = ADAPTERS[name]
        if names and name not in names:
            continue
        if mod.META.get('needs_key') or mod.META.get('any_host'):
            print(f'{name:18s}   —      anahtar gerekli / elle noktalar: atlandı')
            continue
        await one(name, mod)
    await fetch.close()


if __name__ == '__main__':
    asyncio.run(main(set(sys.argv[1:])))
