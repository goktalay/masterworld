"""Kaynaklara giden GÜVENLİ istemci + paylaşılan önbellek (docs §4.1, §5).

- Yalnız https ve adaptörün sabit `hosts` beyaz listesi (elle eklenen noktalarda `any_host=True`: yine de iç ağ reddi).
- Her istekte ad çözümü → tüm adresler genel olmalı (özel / döngü / bağlantı-yerel / CGNAT / çok noktaya yayın reddedilir).
- Yönlendirme izlenmez (3xx → hata); yanıt akış hâlinde okunur, sınır aşılınca kesilir; süre sınırı.
- Kaynak başına token bucket (dakikada `rate_per_min`); hata sonrası üstel geri çekilme.
- Önbellek: anahtar başına (değer, bitiş, bayat bitiş); aynı anahtara eşzamanlı istekler tek istekte birleşir (singleflight).
"""
import asyncio
import ipaddress
import json
import socket
import time
from urllib.parse import urlsplit

import httpx

from . import config


class FetchError(Exception):
    """Kaynak isteği başarısız; mesaj YALNIZ günlüğe (istemciye tek tip kod döner)."""


class RateLimited(FetchError):
    pass


def _ip_ok(ip):
    a = ipaddress.ip_address(ip)
    if a.version == 6 and a.ipv4_mapped:
        a = a.ipv4_mapped
    return not (a.is_private or a.is_loopback or a.is_link_local or a.is_multicast or a.is_reserved or a.is_unspecified
                or (a.version == 4 and a in ipaddress.ip_network('100.64.0.0/10')))


async def host_ok(host):
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        return False
    return bool(infos) and all(_ip_ok(i[4][0]) for i in infos)


class Bucket:
    """burst: tek yenilemede birden çok dosya isteyen adaptörler (META['burst'], ör. celestrak grupları, caltrans bölgeleri)."""
    def __init__(self, per_min, burst=1):
        self.set_rate(per_min, burst)
        self.tokens = self.cap
        self.t = time.monotonic()

    def set_rate(self, per_min, burst=1):
        self.rate = max(0.1, float(per_min)) / 60.0
        self.cap = max(1.0, float(burst or 1), min(10.0, float(per_min) / 6))

    def take(self):
        now = time.monotonic()
        self.tokens = min(self.cap, self.tokens + (now - self.t) * self.rate)
        self.t = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


_buckets = {}
_backoff = {}          # slug → (bekleme bitişi, art arda hata sayısı)
_cache = {}            # anahtar → [değer, taze bitiş, bayat bitiş]
_locks = {}
CACHE_MAX = 4000
_client = None


def client():
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(config.FETCH_TIMEOUT_S, connect=8), follow_redirects=False,
                                    headers={'User-Agent': config.USER_AGENT, 'Accept-Encoding': 'gzip, deflate'},
                                    limits=httpx.Limits(max_connections=64, max_keepalive_connections=16))
    return _client


async def close():
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def cache_peek(key):
    """(değer, taze_mi) ya da (None, False)."""
    c = _cache.get(key)
    if not c:
        return None, False
    now = time.time()
    if now > c[2]:
        _cache.pop(key, None)
        return None, False
    return c[0], now <= c[1]


def cache_put(key, value, ttl, stale=None):
    if len(_cache) >= CACHE_MAX:   # en eski bitişliler atılır
        for k, _ in sorted(_cache.items(), key=lambda kv: kv[1][2])[:CACHE_MAX // 10]:
            _cache.pop(k, None)
    now = time.time()
    _cache[key] = [value, now + ttl, now + (stale if stale is not None else max(ttl * 20, 600))]


async def cached(key, ttl, producer, stale=None):
    """Önbellekli üretim: taze varsa döner; yoksa tek istekle üretir. Üretim hata verirse bayat kopya (varsa) döner.
    Dönüş (değer, bayat_mı)."""
    val, fresh = cache_peek(key)
    if fresh:
        return val, False
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        val2, fresh2 = cache_peek(key)
        if fresh2:
            return val2, False
        try:
            new = await producer()
        except FetchError:
            if val2 is not None:
                return val2, True
            raise
        finally:
            if len(_locks) > CACHE_MAX:
                _locks.clear()
        cache_put(key, new, ttl, stale)
        return new, False


class Ctx:
    """Adaptöre verilen istek bağlamı: kaynak başına beyaz liste + oran + boyut sınırları."""

    def __init__(self, slug, hosts, rate_per_min, any_host=False, api_key=None, burst=1):
        self.slug, self.hosts, self.any_host, self.api_key = slug, tuple(hosts or ()), any_host, api_key
        b = _buckets.get(slug)
        if b is None:
            b = _buckets[slug] = Bucket(rate_per_min, burst)
        else:
            b.set_rate(rate_per_min, burst)
        self.bucket = b

    async def _get(self, url, headers=None, max_bytes=None, accept=None, method='GET', data=None):
        u = urlsplit(url)
        host = (u.hostname or '').lower()
        if u.scheme != 'https' or not host or u.username or u.password or (u.port not in (None, 443)):
            raise FetchError(f'{self.slug}: izin verilmeyen adres biçimi')
        if not self.any_host and host not in self.hosts:
            raise FetchError(f'{self.slug}: beyaz liste dışı host {host}')
        if config.OFFLINE:
            from tests import fixtures   # yalnız testler
            return fixtures.respond(self.slug, url) if method == 'GET' else fixtures.respond(self.slug, url, method=method, data=data)
        wait = _backoff.get(self.slug)
        if wait and time.time() < wait[0]:
            raise FetchError(f'{self.slug}: geri çekilmede')
        if not self.bucket.take():
            raise RateLimited(f'{self.slug}: kaynak oran sınırı')
        if not await host_ok(host):
            raise FetchError(f'{self.slug}: {host} genel olmayan adrese çözülüyor')
        limit = max_bytes or config.FETCH_MAX_BYTES
        h = {'Accept': accept or 'application/json, */*;q=0.5'} | (headers or {})
        try:
            async with client().stream(method, url, headers=h, data=data) as r:
                if r.status_code != 200:
                    raise FetchError(f'{self.slug}: HTTP {r.status_code}')
                cl = r.headers.get('content-length')
                if cl and cl.isdigit() and int(cl) > limit:
                    raise FetchError(f'{self.slug}: yanıt çok büyük ({cl})')
                buf = bytearray()
                async for chunk in r.aiter_bytes():
                    buf += chunk
                    if len(buf) > limit:
                        raise FetchError(f'{self.slug}: yanıt sınırı aşıldı')
                ctype = r.headers.get('content-type', '')
        except httpx.HTTPError as e:
            self._fail()
            raise FetchError(f'{self.slug}: {type(e).__name__}') from None
        except FetchError:
            self._fail()
            raise
        _backoff.pop(self.slug, None)
        return bytes(buf), ctype

    def _fail(self):
        _, n = _backoff.get(self.slug, (0, 0))
        n += 1
        _backoff[self.slug] = (time.time() + min(300, 2 ** min(n, 8)), n)

    async def get_bytes(self, url, headers=None, max_bytes=None, accept=None):
        return await self._get(url, headers, max_bytes, accept)

    async def post_form(self, url, form, headers=None, max_bytes=None):
        """Form gövdeli POST (yalnız OAuth2 belirteç alma gibi zorunlu durumlar; aynı host / IP / boyut / oran denetimleri) → JSON."""
        data, _ = await self._get(url, headers, max_bytes or 64 * 1024, method='POST', data=dict(form))
        try:
            return json.loads(data)
        except ValueError:
            raise FetchError(f'{self.slug}: JSON değil') from None

    async def get_text(self, url, headers=None, max_bytes=None):
        data, _ = await self._get(url, headers, max_bytes, accept='text/plain, text/csv, application/xml, */*;q=0.5')
        return data.decode('utf-8', 'replace')

    async def get_json(self, url, headers=None, max_bytes=None):
        data, _ = await self._get(url, headers, max_bytes)
        try:
            return json.loads(data)
        except ValueError:
            raise FetchError(f'{self.slug}: JSON değil') from None
