"""Çevrimdışı test yanıtları (MW_OFFLINE=1): app.fetch.Ctx ağ yerine respond(slug, url) çağırır.
Dosyalar tests/fixtures/<adaptör>/ altında; gerçek yanıtlardan küçültülmüş örnekler (anahtarlı kaynaklarda belgeden örnek).
slug → adaptör: ':' sonrası atılır (ör. 'opensky:auth'), '-' → '_' ve test/smoke öneki ('t-', 'smoke-') düşülür."""
import re
from pathlib import Path

from app.fetch import FetchError

DIR = Path(__file__).resolve().parent / 'fixtures'
CTYPES = {'.json': 'application/json', '.geojson': 'application/geo+json', '.xml': 'text/xml', '.txt': 'text/plain',
          '.csv': 'text/csv', '.png': 'image/png', '.jpg': 'image/jpeg'}
# (adaptör, URL deseni, dosya)
ROUTES = [
    ('adsb_lol', r'^https://api\.adsb\.lol/v2/point/', 'point.json'),
    ('adsb_fi', r'^https://opendata\.adsb\.fi/api/v2/lat/', 'point.json'),
    ('airplanes_live', r'^https://api\.airplanes\.live/v2/point/', 'point.json'),
    ('opensky', r'^https://auth\.opensky-network\.org/.+/token$', 'token.json'),
    ('opensky', r'^https://opensky-network\.org/api/states/all\?', 'states.json'),
    ('celestrak', r'^https://celestrak\.org/NORAD/elements/gp\.php\?GROUP=(stations|visual)&FORMAT=json$', 'gp.json'),
    ('wheretheiss', r'^https://api\.wheretheiss\.at/v1/satellites/25544$', 'iss.json'),
    ('usgs', r'^https://earthquake\.usgs\.gov/earthquakes/feed/v1\.0/summary/all_day\.geojson$', 'all_day.geojson'),
    ('emsc', r'^https://www\.seismicportal\.eu/fdsnws/event/1/query\?format=json', 'query.json'),
    ('afad', r'^https://servisnet\.afad\.gov\.tr/apigateway/deprem/apiv2/event/filter\?', 'filter.json'),
    ('gdacs', r'^https://www\.gdacs\.org/gdacsapi/api/events/geteventlist/EVENTS4APP$', 'events.json'),
    ('eonet', r'^https://eonet\.gsfc\.nasa\.gov/api/v3/events\?status=open$', 'events.json'),
    ('firms', r'^https://firms\.modaps\.eosdis\.nasa\.gov/api/area/csv/[A-Za-z0-9]+/VIIRS_SNPP_NRT/world/1$', 'world.csv'),
    ('swpc_aurora', r'^https://services\.swpc\.noaa\.gov/json/ovation_aurora_latest\.json$', 'ovation.json'),
    ('open_meteo', r'^https://api\.open-meteo\.com/v1/forecast\?', 'forecast.json'),
    ('metar', r'^https://aviationweather\.gov/api/data/metar\?bbox=', 'metar.json'),
    ('ndbc', r'^https://www\.ndbc\.noaa\.gov/activestations\.xml$', 'activestations.xml'),
    ('ndbc', r'^https://www\.ndbc\.noaa\.gov/data/latest_obs/latest_obs\.txt$', 'latest_obs.txt'),
    ('sondehub', r'^https://api\.v2\.sondehub\.org/sondes\?last=3600$', 'sondes.json'),
    ('safecast', r'^https://api\.safecast\.org/measurements\.json\?', 'measurements.json'),
    ('sensor_community', r'^https://data\.sensor\.community/static/v2/data\.dust\.min\.json$', 'dust.json'),
    ('rainviewer', r'^https://api\.rainviewer\.com/public/weather-maps\.json$', 'maps.json'),
    ('rainviewer', r'^https://tilecache\.rainviewer\.com/v2/radar/[0-9a-f]+/256/\d+/\d+/\d+/2/1_1\.png$', 'tile.png'),
    ('windy_webcams', r'^https://api\.windy\.com/webcams/api/v3/webcams\?', 'webcams.json'),
    ('windy_webcams', r'^https://imgproxy\.windy\.com/', '../digitraffic_cam/cam.jpg'),
    ('caltrans_cctv', r'^https://cwwp2\.dot\.ca\.gov/data/d7/cctv/cctvStatusD07\.json$', 'd07.json'),
    ('caltrans_cctv', r'^https://cwwp2\.dot\.ca\.gov/data/d7/cctv/image/', '../digitraffic_cam/cam.jpg'),
    ('digitraffic_cam', r'^https://tie\.digitraffic\.fi/api/weathercam/v1/stations$', 'stations.json'),
    ('digitraffic_cam', r'^https://weathercam\.digitraffic\.fi/[A-Z0-9]+\.jpg$', 'cam.jpg'),
    ('radio_browser', r'^https://[a-z0-9]+\.api\.radio-browser\.info/json/stations/search\?', 'stations.json'),
    ('submarine_cables', r'^https://www\.submarinecablemap\.com/api/v3/cable/cable-geo\.json$', 'cable-geo.json'),
    ('submarine_cables', r'^https://www\.submarinecablemap\.com/api/v3/landing-point/landing-point-geo\.json$', 'landing-point-geo.json'),
]
_ROUTES = [(a, re.compile(p), f) for a, p, f in ROUTES]
CALLS = []   # (adaptör, yöntem, url) — testler isteklerin biçimini denetleyebilsin


def adapter_of(slug):
    s = str(slug).split(':')[0].replace('-', '_')
    for pre in ('t_', 'smoke_'):
        if s.startswith(pre):
            s = s[len(pre):]
    return s


def respond(slug, url, method='GET', data=None):
    a = adapter_of(slug)
    CALLS.append((a, method, url))
    for ra, rx, fn in _ROUTES:
        if ra == a and rx.search(url):
            path = (DIR / a / fn).resolve()
            return path.read_bytes(), CTYPES.get(path.suffix, 'application/octet-stream')
    raise FetchError(f'{slug}: fixture yok ({url})')
