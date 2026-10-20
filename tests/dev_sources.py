"""Geliştirme: hesap servisi olmadan yerel kaynak kaydı (iç uç biçimi, docs §3.3) üretir → /tmp/masterworld-dev-sources.json.
Kullanım: python3 tests/dev_sources.py [çıktı]"""
import json
import sys

S = [  # slug, category, kind, name, adapter, params, attribution, url, default_on, noncommercial
    ('adsb-lol', 'air', 'aircraft', 'adsb.lol', 'adsb_lol', {}, '© adsb.lol contributors (ODbL)', 'https://adsb.lol', 1, 0),
    ('adsb-fi', 'air', 'aircraft', 'adsb.fi', 'adsb_fi', {}, 'adsb.fi', 'https://adsb.fi', 0, 1),
    ('celestrak', 'space', 'satellite', 'CelesTrak', 'celestrak', {'groups': ['stations', 'visual']}, 'CelesTrak', 'https://celestrak.org', 1, 0),
    ('open-notify-where-the-iss-at', 'space', 'iss', 'Where the ISS at', 'wheretheiss', {}, 'wheretheiss.at', 'https://wheretheiss.at', 1, 0),
    ('noaa-swpc', 'space', 'aurora', 'NOAA SWPC aurora', 'swpc_aurora', {}, 'NOAA SWPC', 'https://www.swpc.noaa.gov', 0, 0),
    ('usgs-earthquake', 'natural', 'quake', 'USGS Earthquake', 'usgs', {'feed': 'all_day'}, 'USGS', 'https://earthquake.usgs.gov', 1, 0),
    ('emsc-seismicportal', 'natural', 'quake', 'EMSC SeismicPortal', 'emsc', {}, 'EMSC', 'https://www.seismicportal.eu', 0, 0),
    ('afad-deprem', 'natural', 'quake', 'AFAD Deprem', 'afad', {}, 'AFAD', 'https://deprem.afad.gov.tr', 0, 0),
    ('gdacs', 'natural', 'disaster', 'GDACS', 'gdacs', {}, 'GDACS', 'https://www.gdacs.org', 0, 0),
    ('nasa-eonet', 'natural', 'event', 'NASA EONET', 'eonet', {}, 'NASA EONET', 'https://eonet.gsfc.nasa.gov', 0, 0),
    ('open-meteo', 'weather', 'forecast', 'Open-Meteo', 'open_meteo', {}, 'Open-Meteo (CC BY 4.0)', 'https://open-meteo.com', 1, 0),
    ('aviationweather-gov', 'weather', 'metar', 'aviationweather.gov METAR', 'metar', {}, 'NOAA aviationweather.gov', 'https://aviationweather.gov', 0, 0),
    ('noaa-ndbc', 'weather', 'buoy', 'NOAA NDBC', 'ndbc', {}, 'NOAA NDBC', 'https://www.ndbc.noaa.gov', 0, 0),
    ('rainviewer', 'weather', 'radar', 'RainViewer', 'rainviewer', {}, 'RainViewer', 'https://www.rainviewer.com', 0, 0),
    ('sondehub', 'weather', 'sonde', 'SondeHub', 'sondehub', {}, 'SondeHub', 'https://sondehub.org', 0, 0),
    ('safecast', 'environment', 'radiation', 'Safecast', 'safecast', {}, 'Safecast (CC0)', 'https://safecast.org', 0, 0),
    ('sensor-community', 'environment', 'airquality', 'Sensor.Community', 'sensor_community', {}, 'Sensor.Community (ODbL)', 'https://sensor.community', 0, 0),
    ('digitraffic-cam', 'camera', 'camera', 'Digitraffic Weathercams (Finlandiya)', 'digitraffic_cam', {}, 'Fintraffic / digitraffic.fi (CC BY 4.0)', 'https://www.digitraffic.fi', 1, 0),
    ('caltrans-cctv', 'camera', 'camera', 'Caltrans CCTV', 'caltrans_cctv', {}, 'Caltrans', 'https://cwwp2.dot.ca.gov', 1, 0),
    ('radio-browser', 'radio', 'radio', 'Radio Browser', 'radio_browser', {}, 'radio-browser.info', 'https://www.radio-browser.info', 1, 0),
    ('telegeography-submarine-cable-map', 'infra', 'cable', 'Submarine Cable Map', 'submarine_cables', {}, 'TeleGeography (CC BY-NC-SA)', 'https://www.submarinecablemap.com', 0, 1),
    ('windy-webcams-api-v3', 'camera', 'camera', 'Windy Webcams', 'windy_webcams', {}, 'Windy.com', 'https://www.windy.com/webcams', 0, 0),
]
out = {'version': 'dev', 'sources': [], 'points': {}}
for i, (slug, cat, kind, name, ad, params, att, url, on, nc) in enumerate(S, 1):
    out['sources'].append({'id': i, 'slug': slug, 'category': cat, 'kind': kind, 'name': name, 'data_desc': None, 'adapter': ad, 'params': params,
                           'api_key': None, 'key_required': 1 if ad == 'windy_webcams' else 0, 'noncommercial': nc, 'attribution_required': 1,
                           'attribution': att, 'attribution_url': url, 'license': None, 'rate_per_min': None, 'ttl_s': None, 'enabled': 1,
                           'default_on': on, 'sort': i * 10, 'scale': None})
p = sys.argv[1] if len(sys.argv) > 1 else '/tmp/masterworld-dev-sources.json'
json.dump(out, open(p, 'w'), ensure_ascii=False)
print(p, len(S))
