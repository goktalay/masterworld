"""MASTERWORLD sunucusu (masterworld.app): statik ön yüz + anonim veri uçları (docs/masterworld.md §4). Kullanıcı kimliği tutulmaz."""
import asyncio
import logging
import math
import re
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.staticfiles import StaticFiles

from . import config, engine, fetch, registry, sources

log = logging.getLogger('masterworld')
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
LANGS = ('tr', 'en', 'de', 'fr', 'es', 'ar', 'ru', 'zh')
SLUG_RE = re.compile(r'^[a-z0-9-]{2,40}$')
ID_RE = re.compile(r'^[A-Za-z0-9_.:,~-]{1,80}$')

CSP = ("default-src 'self'; "
       "script-src 'self' https://www.googletagmanager.com https://static.cloudflareinsights.com; "
       "style-src 'self'; "
       "img-src 'self' data: blob: https://gibs.earthdata.nasa.gov https://tiles.openfreemap.org https://www.googletagmanager.com; "
       "font-src 'self' data: https://tiles.openfreemap.org; "
       f"connect-src 'self' {config.MT_URL} https://tiles.openfreemap.org https://gibs.earthdata.nasa.gov "
       "https://www.google-analytics.com https://*.google-analytics.com https://analytics.google.com https://www.googletagmanager.com "
       "https://cloudflareinsights.com; "
       "media-src 'self' https: blob:; worker-src 'self' blob:; child-src 'self' blob:; "
       "frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'")
HEADERS = {'Content-Security-Policy': CSP, 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'strict-origin-when-cross-origin',
           'Permissions-Policy': 'camera=(), microphone=(), geolocation=(self), payment=(), usb=(), fullscreen=(self)',
           'X-Frame-Options': 'DENY', 'Cross-Origin-Opener-Policy': 'same-origin'}


@asynccontextmanager
async def lifespan(app):
    sources.load_all()
    task = asyncio.create_task(registry.loop())
    log.info('MASTERWORLD %s · adaptörler %d · kayıt %s', config.VERSION, len(sources.ADAPTERS),
             config.SOURCES_FILE or config.MT_INTERNAL)
    yield
    task.cancel()
    await fetch.close()


app = FastAPI(title='MASTERWORLD', docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

_RATE = defaultdict(deque)


def client_ip(request):
    return (request.headers.get('cf-connecting-ip') or (request.headers.get('x-forwarded-for') or '').split(',')[0].strip()
            or (request.client.host if request.client else ''))[:64]


def limited(request, key, limit):
    k = f'{key}:{client_ip(request)}'
    q, t = _RATE[k], time.time()
    while q and q[0] < t - 60:
        q.popleft()
    if len(q) >= limit:
        return int(60 - (t - q[0])) + 1
    q.append(t)
    if len(_RATE) > 50000:
        for kk in [kk for kk, v in _RATE.items() if not v or v[-1] < t - 60]:
            _RATE.pop(kk, None)
    return 0


def err(code, status, retry=None):
    r = JSONResponse({'error': code}, status_code=status)
    if retry:
        r.headers['Retry-After'] = str(retry)
    return r


@app.middleware('http')
async def _headers(request: Request, call_next):
    try:
        resp = await call_next(request)
    except Exception:   # ayrıntı sızmasın
        log.exception('işlenmeyen hata: %s', request.url.path)
        resp = err('internal', 500)
    for k, v in HEADERS.items():
        resp.headers.setdefault(k, v)
    p = request.url.path
    if p.startswith('/vendor/'):
        resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif not p.startswith('/api/'):
        resp.headers.setdefault('Cache-Control', 'no-cache')
    return resp


@app.get('/api/meta')
def meta():
    return {'version': config.VERSION, 'mt_url': config.MT_URL, 'mt_app': config.MT_APP, 'ga_id': config.GA_ID, 'langs': list(LANGS)}


@app.get('/api/layers')
def layers(request: Request):
    if (r := limited(request, 'layers', 60)):
        return err('rate_limited', 429, r)
    return JSONResponse(engine.layers(), headers={'Cache-Control': 'public, max-age=30'})


def _f(v, lo, hi):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) and lo <= x <= hi else None


@app.get('/api/data/{slug}')
async def data(slug: str, request: Request, bbox: str = '', lat: str = '', lon: str = ''):
    if not SLUG_RE.match(slug):
        return err('not_found', 404)
    if (r := limited(request, 'data', config.RATE_DATA)):
        return err('rate_limited', 429, r)
    try:
        d = await engine.data(slug, engine.parse_bbox(bbox) if bbox else None, _f(lat, -90, 90), _f(lon, -180, 180))
    except engine.NotFound:
        return err('not_found', 404)
    except engine.Unavailable:
        return err('source_unavailable', 503, 30)
    return JSONResponse(d, headers={'Cache-Control': f"public, max-age={max(5, min(d['ttl'], 300))}"})


@app.get('/api/media/{slug}/{item_id}')
async def media(slug: str, item_id: str, request: Request):
    if not SLUG_RE.match(slug) or not ID_RE.match(item_id):
        return err('not_found', 404)
    if (r := limited(request, 'media', config.RATE_MEDIA)):
        return err('rate_limited', 429, r)
    try:
        body, ctype = await engine.media(slug, item_id)
    except engine.NotFound:
        return err('not_found', 404)
    except engine.Unavailable:
        return err('source_unavailable', 503, 30)
    return Response(body, media_type=ctype, headers={'Cache-Control': 'public, max-age=15', 'Content-Security-Policy': "default-src 'none'"})


@app.get('/api/tile/{slug}/{z}/{x}/{y}')
async def tile(slug: str, z: int, x: int, y: str, request: Request):
    y = y.split('.')[0]
    if not SLUG_RE.match(slug) or not y.isdigit():
        return err('not_found', 404)
    if (r := limited(request, 'tile', config.RATE_TILE)):
        return err('rate_limited', 429, r)
    try:
        body, ctype = await engine.tile(slug, z, x, int(y))
    except engine.NotFound:
        return err('not_found', 404)
    except engine.Unavailable:
        return Response(status_code=204)
    return Response(body, media_type=ctype, headers={'Cache-Control': 'public, max-age=300'})


@app.get('/api/{rest:path}')
def api_404(rest: str):
    return err('not_found', 404)


S = config.STATIC_DIR


def _page(name):
    return FileResponse(S / name, media_type='text/html; charset=utf-8')


@app.get('/')
def index():
    return _page('index.html')


@app.get('/gizlilik')
@app.get('/privacy')
def privacy():
    return _page('privacy.html')


@app.get('/robots.txt')
def robots():
    return Response('User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: https://masterworld.app/sitemap.xml\n', media_type='text/plain')


@app.get('/sitemap.xml')
def sitemap():
    urls = ''.join(f'<url><loc>https://masterworld.app/{p}</loc></url>' for p in ('', 'gizlilik'))
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
                    media_type='application/xml')


@app.get('/favicon.ico')
def favicon():
    return FileResponse(S / 'img' / 'favicon.svg', media_type='image/svg+xml')


for d in ('css', 'js', 'i18n', 'img', 'vendor'):
    if (S / d).is_dir():
        app.mount(f'/{d}', StaticFiles(directory=S / d), name=d)
