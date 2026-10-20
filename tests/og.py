"""Temiz OG görseli (1200×630): arayüz gizli, küre ortada. Kullanım: python tests/og.py [taban_url]"""
import os
import sys
import time

os.environ.setdefault('LD_LIBRARY_PATH', '/home/gelistirici/build/chromelibs/root/usr/lib/x86_64-linux-gnu')
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8650'
EXE = os.path.expanduser('~/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell')
ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=EXE, args=ARGS)
    pg = b.new_page(viewport={'width': 1200, 'height': 630}, bypass_csp=True)   # yalnız gizleme stili için
    pg.goto(BASE + '/?lang=en')
    pg.wait_for_selector('body:not(.booting)', timeout=90000)
    pg.add_style_tag(content='.topbar,.panel,.status,.attrib,.card,.player,.consent,.ck-bar{display:none!important}')
    pg.evaluate("window.__mw.map.jumpTo({center:[38,30], zoom:1.75})")
    time.sleep(25)
    pg.screenshot(path='/tmp/masterworld/og-raw.png', timeout=120000)
    b.close()
