"""MASTERWORLD ayarları (ortam değişkenleri; PROD'da /opt/hepgo/masterworld/.env systemd EnvironmentFile ile gelir)."""
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE / 'static'
VERSION = (BASE / 'VERSION').read_text().strip() if (BASE / 'VERSION').exists() else '0.0.0'
DATA_DIR = Path(os.environ.get('MW_DATA_DIR', '/tmp/masterworld-data'))

# Hesap servisi (mastertool.download): tarayıcı genel adrese gider; kaynak kaydı iç adresten paylaşılan gizliyle çekilir (docs §3.3)
MT_URL = os.environ.get('MW_MT_URL', 'https://mastertool.download').rstrip('/')
MT_INTERNAL = os.environ.get('MW_MT_INTERNAL', 'http://127.0.0.1:8095').rstrip('/')
MT_SHARED_SECRET = os.environ.get('MW_MT_SHARED_SECRET', '')
MT_APP = 'mw'
# Geliştirme / test: kaynak kaydı hesap servisi yerine bu JSON dosyasından (iç uçla aynı biçim)
SOURCES_FILE = os.environ.get('MW_SOURCES_FILE', '')
REGISTRY_REFRESH_S = int(os.environ.get('MW_REGISTRY_REFRESH_S', '60'))

GA_ID = os.environ.get('MW_GA_ID', '').strip()
PUBLIC_ORIGINS = tuple(o.strip().rstrip('/') for o in os.environ.get(
    'MW_PUBLIC_ORIGINS', 'https://masterworld.app,https://www.masterworld.app').split(',') if o.strip())

# Kaynaklara giden istek sınırları (docs §4.1)
FETCH_TIMEOUT_S = 15
FETCH_MAX_BYTES = 8 * 1024 * 1024
FETCH_BIG_MAX_BYTES = 40 * 1024 * 1024
USER_AGENT = f'MASTERWORLD/{VERSION} (+https://masterworld.app)'
MAX_ITEMS = 5000

# İstemci (IP) başına oran sınırları / dk (docs §5)
RATE_DATA = int(os.environ.get('MW_RATE_DATA', '120'))
RATE_MEDIA = int(os.environ.get('MW_RATE_MEDIA', '60'))
RATE_TILE = int(os.environ.get('MW_RATE_TILE', '600'))

# Testlerde dış ağa çıkılmasın: 1 iken ctx istekleri tests/fixtures'tan yanıtlanır (yalnız test sürücüsü ayarlar)
OFFLINE = os.environ.get('MW_OFFLINE', '0') == '1'
