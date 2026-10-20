"""MASTERWORLD ekran görüntüleri (Playwright, headless shell + yazılım WebGL). Kullanım: python tests/shots.py [taban_url] [çıktı_dizini]
Senaryolar: açılış (küre), katman paneli, kamera kartı, radyo çalar, uçaklar yakın, mobil."""
import os
import sys
import time

os.environ.setdefault('LD_LIBRARY_PATH', '/home/gelistirici/build/chromelibs/root/usr/lib/x86_64-linux-gnu')
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8650'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/tmp/masterworld/shots'
EXE = os.path.expanduser('~/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell')
ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required']
os.makedirs(OUT, exist_ok=True)


def run():
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=EXE, args=ARGS)
        ctx = b.new_context(viewport={'width': 1600, 'height': 900}, device_scale_factor=1, locale='tr-TR')
        pg = ctx.new_page()
        pg.on('console', lambda m: errs.append(f'{m.type}: {m.text}') if m.type in ('error', 'warning') else None)
        pg.on('pageerror', lambda e: errs.append(f'pageerror: {e}'))
        pg.goto(BASE + '/?lang=tr', wait_until='load')
        pg.wait_for_selector('body:not(.booting)', timeout=60000)
        time.sleep(14)
        pg.screenshot(path=f'{OUT}/01-acilis.png', timeout=120000)
        # Avrupa'ya yaklaş (uçak, kamera, deprem)
        pg.evaluate("window.__mw && window.__mw.map.jumpTo({center:[25,50], zoom:3.6})")
        time.sleep(12)
        pg.screenshot(path=f'{OUT}/02-avrupa.png', timeout=120000)
        # Finlandiya kamerası: ilk kamera öğesine odaklan
        pg.evaluate("""(() => { const L = window.__mw.layers; const its = L.items.get('digitraffic-cam'); if (!its) return;
            const it = [...its.values()][0]; L.focus(L.defs.get('digitraffic-cam'), it); })()""")
        time.sleep(10)
        pg.screenshot(path=f'{OUT}/03-kamera.png', timeout=120000)
        # Radyo
        pg.evaluate("""(() => { const L = window.__mw.layers; const its = L.items.get('radio-browser'); if (!its) return;
            const it = [...its.values()].find(x => x.p && x.p.country) || [...its.values()][0]; L.focus(L.defs.get('radio-browser'), it); })()""")
        time.sleep(8)
        pg.screenshot(path=f'{OUT}/04-radyo.png', timeout=120000)
        # Uçaklar yakın (İstanbul)
        pg.keyboard.press('Escape')
        pg.evaluate("window.__mw.map.jumpTo({center:[28.9,41.0], zoom:7.2, pitch:45})")
        time.sleep(12)
        pg.screenshot(path=f'{OUT}/05-ucaklar.png', timeout=120000)
        pg.evaluate("""(() => { const L = window.__mw.layers; const its = L.items.get('adsb-lol'); if (!its) return;
            const it = [...its.values()].find(x => !x.p.ground) ; if (it) L.focus(L.defs.get('adsb-lol'), it); })()""")
        time.sleep(5)
        pg.screenshot(path=f'{OUT}/06-ucak-kart.png', timeout=120000)
        ctx.close()
        m = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale='en-US')
        mp = m.new_page()
        mp.on('pageerror', lambda e: errs.append(f'mobile pageerror: {e}'))
        mp.goto(BASE + '/', wait_until='load')
        mp.wait_for_selector('body:not(.booting)', timeout=60000)
        time.sleep(12)
        mp.screenshot(path=f'{OUT}/07-mobil.png', timeout=120000)
        mp.click('#btn-layers')
        time.sleep(2)
        mp.screenshot(path=f'{OUT}/08-mobil-panel.png', timeout=120000)
        b.close()
    print('\n'.join(errs[:60]) or 'konsol hatası yok')


run()
