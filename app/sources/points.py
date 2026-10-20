"""Elle eklenen tekil noktalar (Merkez › MASTERWORLD › Noktalar; hesap servisi mw_points). Kamera görüntüsü vekilden geçer
(any_host: yönetici adresi; iç ağ reddi yine geçerli), radyo akışı p.stream ile tarayıcıda doğrudan çalar."""
from . import clip, num, ok_coord
from .. import registry

META = {'mode': 'global', 'ttl': 30, 'rate_per_min': 60, 'hosts': (), 'any_host': True, 'kind': 'camera', 'needs_key': False, 'refresh_s': 120}


async def fetch(ctx, src, q):
    out = []
    for p in registry.points(src.get('id')):
        lat, lon = num(p.get('lat')), num(p.get('lon'))
        if not ok_coord(lat, lon):
            continue
        url, mt = str(p.get('media_url') or ''), p.get('media_type')
        props = {k: clip(v, 200) for k, v in (p.get('props') or {}).items() if isinstance(v, (str, int, float))} if isinstance(p.get('props'), dict) else {}
        it = {'id': str(p.get('id')), 'lat': lat, 'lon': lon, 'name': clip(p.get('name'), 120) or '—', 'p': props}
        if url.startswith('https://'):
            if mt in ('image', 'mjpeg'):
                it['_media'] = url
                it['p']['media'] = 'image'
            elif mt == 'audio':
                it['p']['stream'] = url
            elif mt == 'link':
                it['p']['url'] = url
        out.append(it)
    return {'items': out}
