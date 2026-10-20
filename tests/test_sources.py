"""Adaptör ve güvenli istemci testleri (ağsız). Çalıştırma:
    cd <depo> && MW_OFFLINE=1 /opt/hepgo/fabrika-yonetim/.venv/bin/python -m unittest tests.test_sources -v
"""
import json
import os
import re
import tempfile
import unittest
from unittest import mock
from urllib.parse import urlsplit

os.environ['MW_OFFLINE'] = '1'

import httpx  # noqa: E402

from app import config, engine, fetch, registry  # noqa: E402
from app.sources import ADAPTERS, load_all, safe_id  # noqa: E402
from tests import fixtures  # noqa: E402

ID_RE = re.compile(r'^[A-Za-z0-9_.:,~-]{1,80}$')
ITEM_KEYS = {'id', 'lat', 'lon', 'alt', 'name', 'hdg', 'spd', 't', 'p', '_media'}
KEYS = {'opensky': 'test-client:test-secret', 'firms': 'a' * 32, 'windy_webcams': 'windy-test-key'}
BBOX_Q = {'metar': (20.0, 40.0, 30.0, 50.0), 'windy_webcams': (150.0, -40.0, 160.0, -30.0), 'opensky': (20.0, 30.0, 30.0, 40.0)}
MIN_ITEMS = {'adsb_fi': 6, 'adsb_lol': 4, 'airplanes_live': 4, 'opensky': 3, 'celestrak': 6, 'wheretheiss': 1, 'emsc': 6, 'afad': 6,
             'gdacs': 5, 'eonet': 7, 'firms': 4, 'swpc_aurora': 30, 'open_meteo': 1, 'metar': 6, 'ndbc': 5, 'sondehub': 5,
             'safecast': 2, 'sensor_community': 5, 'windy_webcams': 2, 'caltrans_cctv': 2, 'digitraffic_cam': 5, 'radio_browser': 4,
             'submarine_cables': 5, 'usgs': 2, 'points': 2}

load_all()
config.OFFLINE = True


def slug_of(name):
    return 't-' + name.replace('_', '-')


def make_registry():
    srcs = []
    for i, name in enumerate(sorted(ADAPTERS), 1):
        m = ADAPTERS[name].META
        srcs.append({'id': i, 'slug': slug_of(name), 'category': 'test', 'kind': m.get('kind'), 'name': name, 'adapter': name,
                     'params': {'groups': ['stations', 'visual']} if name == 'celestrak' else {}, 'api_key': KEYS.get(name),
                     'key_required': 1 if m.get('needs_key') else 0, 'enabled': 1, 'default_on': 0, 'sort': i})
    pid = next(s['id'] for s in srcs if s['adapter'] == 'points')
    pts = {str(pid): [{'id': 1, 'name': 'Elle kamera', 'lat': 41.0, 'lon': 29.0, 'media_type': 'image', 'media_url': 'https://example.org/c.jpg', 'props': {}},
                      {'id': 2, 'name': 'Elle radyo', 'lat': 39.9, 'lon': 32.8, 'media_type': 'audio', 'media_url': 'https://example.org/s.mp3', 'props': {'country': 'TR'}}]}
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump({'version': 'test', 'sources': srcs, 'points': pts}, f)
    registry.load_file(f.name)
    os.unlink(f.name)


make_registry()


def q_for(name, m):
    if m.get('mode') == 'bbox':
        w, s, e, n = BBOX_Q.get(name, (25.0, 40.0, 30.0, 45.0))
        return {'cell': (w, s, e, n), 'lat': (s + n) / 2, 'lon': (w + e) / 2, 'radius_nm': 200}
    if m.get('mode') == 'point':
        return {'lat': 41.0, 'lon': 29.0}
    return {}


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def run_adapter(self, name):
        mod = ADAPTERS[name]
        src = registry.get(slug_of(name))
        res = await mod.fetch(engine.ctx_of(src), src, q_for(name, mod.META))
        self.check(name, mod, res)
        return res

    def check(self, name, mod, res):
        items = res.get('items')
        self.assertIsInstance(items, list, name)
        self.assertGreaterEqual(len(items), MIN_ITEMS.get(name, 1), name)
        ids = set()
        for it in items:
            self.assertLessEqual(set(it), ITEM_KEYS, f'{name}: beklenmeyen alan {set(it) - ITEM_KEYS}')
            self.assertTrue(ID_RE.match(str(it['id'])), f'{name}: id {it["id"]!r}')
            self.assertNotIn(it['id'], ids, f'{name}: yinelenen id {it["id"]}')
            ids.add(it['id'])
            self.assertIsInstance(it['lat'], float | int, name)
            self.assertTrue(-90 <= it['lat'] <= 90 and -180 <= it['lon'] <= 180, f'{name}: koordinat {it["lat"]},{it["lon"]}')
            self.assertIsInstance(it.get('name'), str, name)
            self.assertTrue(it['name'], name)
            self.assertLessEqual(len(it['name']), 160, name)
            p = it.get('p', {})
            self.assertIsInstance(p, dict, name)
            self.assertFalse([k for k, v in p.items() if v is None], f'{name}: p içinde None')
            self.assertFalse([k for k in p if k.startswith('_')], f'{name}: p içinde gizli alan')
            for k in ('t', 'alt', 'hdg', 'spd'):
                if it.get(k) is not None:
                    self.assertIsInstance(it[k], float | int, f'{name}.{k}')
            if '_media' in it:
                u = urlsplit(it['_media'])
                self.assertEqual(u.scheme, 'https', name)
                self.assertIn(u.hostname, getattr(mod, 'MEDIA_HOSTS', None) or (u.hostname,), name)
            for k in ('url', 'stream', 'favicon', 'hls'):
                if k in p:
                    self.assertTrue(str(p[k]).startswith('https://'), f'{name}: p.{k} https değil: {p[k]}')
        for ln in res.get('lines') or []:
            self.assertTrue(ID_RE.match(ln['id']), ln['id'])
            self.assertGreaterEqual(len(ln['coords']), 2)
            for lon, lat in ln['coords']:
                self.assertTrue(-90 <= lat <= 90 and -180 <= lon <= 180)

    async def test_all_adapters(self):
        for name, mod in sorted(ADAPTERS.items()):
            if mod.META.get('mode') == 'tile':
                continue
            with self.subTest(adapter=name):
                await self.run_adapter(name)

    async def test_meta(self):
        for name, mod in ADAPTERS.items():
            m = mod.META
            with self.subTest(adapter=name):
                self.assertIn(m['mode'], ('global', 'bbox', 'point', 'tile'))
                self.assertTrue(0.1 <= m['rate_per_min'] <= 600)
                self.assertTrue(5 <= m['ttl'] <= 86400)
                self.assertIsInstance(m['kind'], str)
                self.assertIn('needs_key', m)
                if not m.get('any_host'):
                    self.assertTrue(m['hosts'] and all(isinstance(h, str) and '.' in h for h in m['hosts']))

    async def test_celestrak_omm_and_kepler(self):
        from app.sources import celestrak
        res = await self.run_adapter('celestrak')
        iss = next(it for it in res['items'] if it['id'] == '25544')
        for k in ('MEAN_MOTION', 'ECCENTRICITY', 'INCLINATION', 'RA_OF_ASC_NODE', 'ARG_OF_PERICENTER', 'MEAN_ANOMALY', 'EPOCH', 'BSTAR',
                  'NORAD_CAT_ID', 'OBJECT_NAME'):
            self.assertIn(k, iss['p']['omm'])
        self.assertTrue(300 < iss['p']['alt_km'] < 500)
        # gerçek gözlem: wheretheiss 1792494853 anında lat 4.17, lon −154.07; kaba Kepler birkaç yüz km içinde olmalı
        omm = json.loads((fixtures.DIR / 'celestrak' / 'gp.json').read_text())[0]
        lat, lon, alt = celestrak.kepler_subpoint(omm, 1792494853)
        self.assertLess(abs(lat - 4.17), 5)
        self.assertLess(abs(((lon + 154.07 + 540) % 360) - 180), 5)

    async def test_specifics(self):
        r = await self.run_adapter('radio_browser')
        self.assertTrue(all(it['p']['stream'].startswith('https://') for it in r['items']))
        self.assertFalse(any(it['id'].endswith('0bad') for it in r['items']))
        self.assertTrue(all(len(it['p'].get('tags', [])) <= 5 for it in r['items']))
        r = await self.run_adapter('caltrans_cctv')
        ids = {it['id'] for it in r['items']}
        self.assertEqual(ids, {'d7-1', 'd7-3'})          # hizmet dışı (inService false) atlanır
        hls = [it for it in r['items'] if it['p'].get('hls')]
        self.assertEqual(len(hls), 1)
        r = await self.run_adapter('swpc_aurora')
        self.assertTrue(all(it['p']['prob'] >= 10 and it['p']['rank'] == it['p']['prob'] for it in r['items']))
        self.assertTrue(any(it['lon'] == -1 for it in r['items']))       # 359 → −1
        r = await self.run_adapter('open_meteo')
        self.assertEqual(len(r['data']['hourly']['time']), 24)
        self.assertIn('temperature_2m', r['data']['current'])
        r = await self.run_adapter('firms')
        frps = [it['p']['frp'] for it in r['items']]
        self.assertEqual(frps, sorted(frps, reverse=True))
        self.assertEqual(len(r['items']), 4)                            # lat 95 atlanır
        r = await self.run_adapter('windy_webcams')
        self.assertEqual({it['id'] for it in r['items']}, {'1179853135', '1500000002'})
        self.assertTrue(all(it['p']['url'].startswith('https://www.windy.com/') for it in r['items']))
        self.assertEqual(sum(1 for it in r['items'] if '_media' in it), 1)
        r = await self.run_adapter('sensor_community')
        self.assertNotIn('999999', {it['id'] for it in r['items']})     # iç mekân
        r = await self.run_adapter('eonet')
        poly = next(it for it in r['items'] if it['id'] == 'EONET_TEST_POLY')
        self.assertAlmostEqual(poly['lat'], -69.2, places=1)
        r = await self.run_adapter('submarine_cables')
        self.assertTrue(r['lines'] and all('~' in ln['id'] for ln in r['lines']))

    async def test_request_shapes(self):
        fixtures.CALLS.clear()
        await self.run_adapter('metar')
        url = next(u for a, _, u in fixtures.CALLS if a == 'metar')
        self.assertIn('bbox=40,20,50,30&', url)                         # güney,batı,kuzey,doğu
        fixtures.CALLS.clear()
        from app.sources import opensky
        opensky._tok.clear()
        await self.run_adapter('opensky')
        await self.run_adapter('opensky')
        posts = [c for c in fixtures.CALLS if c[1] == 'POST']
        self.assertEqual(len(posts), 1)                                 # belirteç önbellekte
        self.assertTrue(posts[0][2].startswith('https://auth.opensky-network.org/'))
        fixtures.CALLS.clear()
        await self.run_adapter('windy_webcams')
        url = next(u for a, _, u in fixtures.CALLS if a == 'windy_webcams')
        self.assertIn('bbox=-30,160,-40,150&', url)                     # kuzey,doğu,güney,batı

    async def test_key_validation(self):
        from app.sources import firms, opensky
        src = dict(registry.get(slug_of('firms')), api_key='../etc')
        with self.assertRaises(fetch.FetchError):
            await firms.fetch(engine.ctx_of(src), src, {})
        src = dict(registry.get(slug_of('opensky')), api_key='yalnizid')
        opensky._tok.clear()
        with self.assertRaises(fetch.FetchError):
            await opensky.fetch(engine.ctx_of(src), src, q_for('opensky', opensky.META))

    def test_safe_id(self):
        self.assertEqual(safe_id('a b/c?d'), 'a_b_c_d')
        self.assertIsNone(safe_id('  '))
        self.assertEqual(len(safe_id('x' * 200)), 80)
        self.assertTrue(ID_RE.match(safe_id('Ünïcode id #1')))


class EngineFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_global(self):
        d = await engine.data('t-usgs')
        self.assertEqual(d['mode'], 'global')
        self.assertEqual(len(d['items']), 2)
        d = await engine.data('t-usgs', bbox=(-170.0, 50.0, -150.0, 60.0))
        self.assertEqual([it['id'] for it in d['items']], ['us7000abcd'])

    async def test_global_lines(self):
        d = await engine.data('t-submarine-cables')
        self.assertTrue(d['lines'])

    async def test_bbox(self):
        d = await engine.data('t-adsb-fi', bbox=(26.0, 40.0, 30.0, 43.0))
        self.assertEqual(d['mode'], 'bbox')
        self.assertTrue(d['items'])
        self.assertTrue(all(26 <= it['lon'] <= 30 and 40 <= it['lat'] <= 43 for it in d['items']))

    async def test_point(self):
        d = await engine.data('t-open-meteo', lat=41.03, lon=29.02)
        self.assertEqual(d['mode'], 'point')
        self.assertEqual(len(d['items']), 1)
        self.assertIn('hourly', d['data'])

    async def test_tile(self):
        body, ctype = await engine.tile('t-rainviewer', 3, 4, 2)
        self.assertEqual(ctype, 'image/png')
        self.assertTrue(body.startswith(b'\x89PNG'))
        with self.assertRaises(engine.NotFound):
            await engine.tile('t-rainviewer', 8, 1, 1)                 # ücretsiz katman z ≤ 7

    async def test_media_hidden_and_proxied(self):
        d = await engine.data('t-digitraffic-cam')
        it = d['items'][0]
        self.assertNotIn('_media', it)
        self.assertEqual(it['p']['media'], 'image')
        self.assertNotIn('weathercam', json.dumps(d))                   # görüntü adresi istemciye sızmaz
        body, ctype = await engine.media('t-digitraffic-cam', it['id'])
        self.assertEqual(ctype, 'image/jpeg')
        d = await engine.data('t-caltrans-cctv')
        body, ctype = await engine.media('t-caltrans-cctv', 'd7-1')
        self.assertEqual(ctype, 'image/jpeg')
        with self.assertRaises(engine.NotFound):
            await engine.media('t-caltrans-cctv', 'yok')

    async def test_key_missing_not_live(self):
        src = dict(registry.get('t-firms'), api_key=None)
        self.assertFalse(engine.is_live(src))

    async def test_layers_no_key(self):
        self.assertNotIn('windy-test-key', json.dumps(engine.layers()))


class FetchSecurityTests(unittest.IsolatedAsyncioTestCase):
    def test_ip_ok(self):
        for ip in ('127.0.0.1', '10.1.2.3', '192.168.1.1', '172.16.0.1', '169.254.169.254', '::1', '100.64.0.1', '::ffff:10.0.0.1',
                   'fc00::1', 'fe80::1', '0.0.0.0', '224.0.0.1'):
            self.assertFalse(fetch._ip_ok(ip), ip)
        for ip in ('8.8.8.8', '1.1.1.1', '2606:4700:4700::1111'):
            self.assertTrue(fetch._ip_ok(ip), ip)

    async def test_host_ok_local(self):
        self.assertFalse(await fetch.host_ok('localhost'))
        self.assertFalse(await fetch.host_ok('127.0.0.1'))

    async def test_url_rules(self):
        ctx = fetch.Ctx('t-sec', ('api.example.org',), 60)
        for url in ('http://api.example.org/x', 'https://evil.example.org/x', 'https://user:pw@api.example.org/x',
                    'https://api.example.org:8443/x', 'ftp://api.example.org/x', 'https:///x'):
            with self.subTest(url=url), self.assertRaises(fetch.FetchError):
                await ctx.get_json(url)

    async def _live_path(self, handler, url='https://api.example.org/x', max_bytes=None):
        """OFFLINE kapalıyken gerçek _get yolunu sahte taşıyıcıyla çalıştırır (ad çözümü denetimi sahte: genel)."""
        old = fetch._client
        fetch._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)
        fetch._backoff.clear()
        try:
            with mock.patch.object(config, 'OFFLINE', False), mock.patch.object(fetch, 'host_ok', mock.AsyncMock(return_value=True)):
                return await fetch.Ctx('t-sec2', ('api.example.org',), 600).get_bytes(url, max_bytes=max_bytes)
        finally:
            await fetch._client.aclose()
            fetch._client = old
            fetch._backoff.clear()

    async def test_size_limit(self):
        big = b'x' * (64 * 1024)
        with self.assertRaises(fetch.FetchError):
            await self._live_path(lambda r: httpx.Response(200, content=big), max_bytes=1024)
        with self.assertRaises(fetch.FetchError):                       # içerik uzunluğu üstbilgisi de denetlenir
            await self._live_path(lambda r: httpx.Response(200, content=big, headers={'content-length': str(10 ** 9)}), max_bytes=1024)
        body, _ = await self._live_path(lambda r: httpx.Response(200, content=b'{"ok":1}'), max_bytes=1024)
        self.assertEqual(body, b'{"ok":1}')

    async def test_redirect_not_followed(self):
        with self.assertRaises(fetch.FetchError):
            await self._live_path(lambda r: httpx.Response(302, headers={'location': 'https://169.254.169.254/'}))

    async def test_private_resolution_rejected(self):
        with mock.patch.object(config, 'OFFLINE', False):
            fetch._backoff.clear()
            ctx = fetch.Ctx('t-sec3', ('localhost',), 600)
            with self.assertRaises(fetch.FetchError):
                await ctx.get_json('https://localhost/x')


if __name__ == '__main__':
    unittest.main()
