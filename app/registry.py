"""Kaynak kaydı: hesap servisinin iç ucundan (docs §3.3) periyodik çekilir; son başarılı kopya diske yazılır (servis düşerse onunla açılır).
Geliştirme / testte MW_SOURCES_FILE aynı biçimdeki JSON'dan okunur."""
import asyncio
import json
import logging
import os
import time

import httpx

from . import config

log = logging.getLogger('masterworld.registry')
CACHE_FILE = config.DATA_DIR / 'sources.json'
_state = {'version': None, 'sources': {}, 'points': {}, 'loaded_at': 0.0}


def _apply(d):
    src = {}
    for s in d.get('sources') or []:
        if isinstance(s, dict) and s.get('slug'):
            s['params'] = s.get('params') if isinstance(s.get('params'), dict) else _json(s.get('params'))
            src[s['slug']] = s
    pts = {}
    for sid, lst in (d.get('points') or {}).items():
        pts[str(sid)] = [p for p in lst or [] if isinstance(p, dict)]
    _state.update(version=d.get('version'), sources=src, points=pts, loaded_at=time.time())


def _json(v):
    try:
        x = json.loads(v or '{}')
        return x if isinstance(x, dict) else {}
    except (TypeError, ValueError):
        return {}


def load_file(path):
    with open(path, encoding='utf-8') as f:
        _apply(json.load(f))


async def refresh():
    if config.SOURCES_FILE:
        load_file(config.SOURCES_FILE)
        return True
    if not config.MT_SHARED_SECRET:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f'{config.MT_INTERNAL}/api/mw/internal/sources', headers={'X-Masterworld-Secret': config.MT_SHARED_SECRET})
        if r.status_code != 200:
            log.warning('kaynak kaydı alınamadı: HTTP %s', r.status_code)
            return False
        d = r.json()
    except (httpx.HTTPError, ValueError) as e:
        log.warning('kaynak kaydı alınamadı: %s', type(e).__name__)
        return False
    _apply(d)
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CACHE_FILE.with_suffix('.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)
        os.chmod(tmp, 0o600)          # API anahtarları içerir
        os.replace(tmp, CACHE_FILE)
    except OSError as e:
        log.warning('kaynak önbelleği yazılamadı: %s', e)
    return True


async def loop():
    if not await refresh() and CACHE_FILE.exists() and not _state['sources']:
        try:
            load_file(CACHE_FILE)
            log.info('kaynak kaydı diskteki son kopyadan yüklendi')
        except (OSError, ValueError):
            pass
    while True:
        await asyncio.sleep(config.REGISTRY_REFRESH_S)
        await refresh()


def sources():
    return _state['sources']


def get(slug):
    return _state['sources'].get(slug)


def points(source_id):
    return _state['points'].get(str(source_id), [])


def version():
    return _state['version']
