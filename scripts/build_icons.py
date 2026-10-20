"""static/js/icons.js PATHS → static/img/icons.svg (arayüz <use> sembolleri) + logo/favicon. Çalıştırma: python3 scripts/build_icons.py"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / 'static/js/icons.js').read_text(encoding='utf-8')
block = src.split('export const PATHS = {', 1)[1].split('\n};', 1)[0]
paths = dict(re.findall(r"^\s*(\w+):\s*'([^']+)'", block, re.M))
LOGO_INNER = """<defs><radialGradient id="mwg" cx="38%" cy="32%" r="75%"><stop offset="0" stop-color="#7dd3fc"/><stop offset=".55" stop-color="#2563eb"/><stop offset="1" stop-color="#0b1a3a"/></radialGradient>
<linearGradient id="mwo" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#22d3ee" stop-opacity=".1"/><stop offset=".6" stop-color="#22d3ee"/><stop offset="1" stop-color="#f0abfc"/></linearGradient></defs>
<circle cx="16" cy="16" r="10.5" fill="url(#mwg)"/>
<g fill="none" stroke="#bae6fd" stroke-opacity=".55" stroke-width=".8"><ellipse cx="16" cy="16" rx="4.6" ry="10.5"/><path d="M5.6 13h20.8M5.6 19h20.8M16 5.5v21"/></g>
<ellipse cx="16" cy="16" rx="15" ry="5.2" transform="rotate(-24 16 16)" fill="none" stroke="url(#mwo)" stroke-width="1.6"/>
<circle cx="28.4" cy="9.6" r="2" fill="#f0abfc"/>"""
syms = ''.join(f'<symbol id="{k}" viewBox="0 0 24 24"><path d="{v}"/></symbol>' for k, v in paths.items())
(ROOT / 'static/img/icons.svg').write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg"><symbol id="logo" viewBox="0 0 32 32">{LOGO_INNER}</symbol>{syms}</svg>\n', encoding='utf-8')
(ROOT / 'static/img/favicon.svg').write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="#05070d"/>{LOGO_INNER}</svg>\n', encoding='utf-8')
print(len(paths), 'simge')
