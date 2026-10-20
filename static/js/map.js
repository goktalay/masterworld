// Küre + altlıklar. MapLibre GL JS 6 (yerel /vendor; worker aynı kökenden). Vektör altlık OpenFreeMap (anahtarsız), raster NASA GIBS (kamu malı).
import * as maplibregl from '/vendor/maplibre-gl/maplibre-gl.mjs';

export { maplibregl };
const OFM = 'https://tiles.openfreemap.org/styles/';
const GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/';
const yday = () => new Date(Date.now() - 36 * 3600e3).toISOString().slice(0, 10);   // GIBS günlük mozaiği ~1 gün gecikir

export const BASES = {
  dark: { label: 'base.dark', thumb: 't-dark', vector: 'dark', attrib: '© OpenStreetMap contributors · OpenFreeMap · OpenMapTiles' },
  light: { label: 'base.light', thumb: 't-light', vector: 'positron', attrib: '© OpenStreetMap contributors · OpenFreeMap · OpenMapTiles' },
  night: { label: 'base.night', thumb: 't-night', raster: () => `${GIBS}VIIRS_Black_Marble/default/2016-01-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png`, maxzoom: 8,
    attrib: 'NASA Earth Observatory / GIBS (Black Marble) · © OpenStreetMap contributors' },
  blue: { label: 'base.blue', thumb: 't-blue', raster: () => `${GIBS}BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg`, maxzoom: 8,
    attrib: 'NASA Blue Marble / GIBS · © OpenStreetMap contributors' },
  today: { label: 'base.today', thumb: 't-today', raster: () => `${GIBS}VIIRS_SNPP_CorrectedReflectance_TrueColor/default/${yday()}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`, maxzoom: 9,
    attrib: 'NASA GIBS · VIIRS SNPP Corrected Reflectance · © OpenStreetMap contributors' },
};

const styleCache = {};
async function vectorStyle(name) {
  if (!styleCache[name]) {
    const r = await fetch(OFM + name);
    if (!r.ok) throw new Error('style');
    styleCache[name] = await r.json();
  }
  return structuredClone(styleCache[name]);
}

// Küre atmosferi: koyu uzay + ufukta mavi hale
const SKY = { 'sky-color': '#0b1a3a', 'horizon-color': '#1e3a8a', 'fog-color': '#0b1220', 'sky-horizon-blend': 0.6, 'horizon-fog-blend': 0.6, 'fog-ground-blend': 0.4,
  'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 1, 5, 1, 7, 0] };

export async function buildStyle(key, { labels = true } = {}) {
  const b = BASES[key] || BASES.dark;
  let st;
  if (b.vector) {
    st = await vectorStyle(b.vector);
    if (b.vector === 'dark') {   // daha derin, "uzay" tonu
      for (const l of st.layers) {
        if (l.type === 'background') l.paint = { ...l.paint, 'background-color': '#070b14' };
        if (l.id === 'water' && l.type === 'fill') l.paint = { ...l.paint, 'fill-color': '#0a1424' };
      }
    }
    if (!labels) st.layers = st.layers.filter(l => l.type !== 'symbol');
  } else {
    const dark = await vectorStyle('dark');
    const keep = dark.layers.filter(l => (labels && l.type === 'symbol' && /place|country|state|water_name/.test(l.id)) || /boundary_(country|state)/.test(l.id));
    for (const l of keep) if (l.type === 'symbol') l.paint = { ...l.paint, 'text-halo-color': 'rgba(0,0,0,0.85)', 'text-halo-width': 1.4 };
    st = { version: 8, glyphs: dark.glyphs, sprite: dark.sprite, sources: { openmaptiles: dark.sources.openmaptiles,
      base: { type: 'raster', tiles: [b.raster()], tileSize: 256, maxzoom: b.maxzoom } },
    layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#000' } }, { id: 'base', type: 'raster', source: 'base',
      paint: { 'raster-fade-duration': 250, ...(key === 'night' ? { 'raster-contrast': 0.15 } : { 'raster-saturation': -0.05 }) } }, ...keep] };
  }
  st.projection = { type: 'globe' };
  st.sky = SKY;
  return st;
}

export async function createMap(container, { base, view, labels }) {
  const style = await buildStyle(base, { labels });
  const map = new maplibregl.Map({
    container, style, attributionControl: false, maxPitch: 70, renderWorldCopies: false, fadeDuration: 150, dragRotate: true,
    center: view ? [view.lng, view.lat] : [32, 30], zoom: view ? view.zoom : 1.6, bearing: view?.bearing || 0, pitch: view?.pitch || 0,
    localIdeographFontFamily: "'Noto Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif",
  });
  map.touchZoomRotate.enableRotation();
  return map;
}

export function firstSymbolId(map) {
  return map.getStyle().layers.find(l => l.type === 'symbol')?.id;
}
