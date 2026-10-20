// Simge yolları (24×24, yalnız dolgu). Arayüz simgeleri /img/icons.svg'den (scripts/build_icons.py bu dosyadan üretir),
// harita simgeleri aynı yollarla tuvalde çizilir (mapIcon). Material Design simgelerinin bir kısmı (Apache-2.0) + özgün çizimler.
export const PATHS = {
  search: 'M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z',
  layers: 'M11.99 18.54l-7.37-5.73L3 14.07l9 7 9-7-1.63-1.27-7.38 5.74zM12 16l7.36-5.73L21 9l-9-7-9 7 1.63 1.27L12 16z',
  globe: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z',
  locate: 'M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm8.94 3A8.99 8.99 0 0 0 13 3.06V1h-2v2.06A8.99 8.99 0 0 0 3.06 11H1v2h2.06A8.99 8.99 0 0 0 11 20.94V23h2v-2.06A8.99 8.99 0 0 0 20.94 13H23v-2h-2.06zM12 19c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z',
  user: 'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z',
  close: 'M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z',
  pause: 'M6 19h4V5H6v14zm8-14v14h4V5h-4z',
  play: 'M8 5v14l11-7z',
  expand: 'M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z',
  link: 'M19 19H5V5h7V3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z',
  chevron: 'M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z',
  plane: 'M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z',
  ship: 'M20 21c-1.39 0-2.78-.47-4-1.32-2.44 1.71-5.56 1.71-8 0C6.78 20.53 5.39 21 4 21H2v2h2c1.38 0 2.74-.35 4-.99 2.52 1.29 5.48 1.29 8 0 1.26.65 2.62.99 4 .99h2v-2h-2zM3.95 19H4c1.6 0 3.02-.88 4-2 .98 1.12 2.4 2 4 2s3.02-.88 4-2c.98 1.12 2.4 2 4 2h.05l1.89-6.68c.08-.26.06-.54-.06-.78s-.34-.42-.6-.5L20 10.62V6c0-1.1-.9-2-2-2h-3V1H9v3H6c-1.1 0-2 .9-2 2v4.62l-1.29.42a1 1 0 0 0-.66 1.28L3.95 19zM6 6h12v3.97L12 8 6 9.97V6z',
  sat: 'M10.6 9.2l4.2 4.2-1.4 1.4-4.2-4.2zM3.5 7.3L7.3 3.5l3.6 3.6-3.8 3.8zM13.1 16.9l3.8-3.8 3.6 3.6-3.8 3.8zM16 2a6 6 0 0 1 6 6h-2a4 4 0 0 0-4-4z',
  iss: 'M1 9h6v6H1zM17 9h6v6h-6zM9 8h6v8H9zM7 11.25h2v1.5H7zM15 11.25h2v1.5h-2z',
  aurora: 'M2 19c2.2-8.4 4.3-13 6.5-13S10.8 15 13 15s3.1-6.5 5.2-6.5S21.6 13 22 19z',
  quake: 'M2 12.5h3.2l2.1-6 3 11.5 3.1-15 2.9 12.2 1.9-2.7H22v2h-2.8l-3.2 4.6-2.1-8.9-3.1 14.5-2.9-11.3-1.4 3.1H2z',
  fire: 'M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8C20 8.61 17.41 3.8 13.5.67zM11.71 19c-1.78 0-3.22-1.4-3.22-3.14 0-1.62 1.05-2.76 2.81-3.12 1.77-.36 3.6-1.21 4.62-2.58.39 1.29.59 2.65.59 4.04 0 2.65-2.15 4.8-4.8 4.8z',
  warning: 'M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z',
  pin: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 0 1 0-5 2.5 2.5 0 0 1 0 5z',
  volcano: 'M2 21l6-10h2.2l1-3h1.6l1 3H16l6 10zM10.5 6.5L9.6 3.8l2.4 1.4 2.4-1.4-.9 2.7z',
  bolt: 'M7 2v11h3v9l7-12h-4l4-8z',
  cloud: 'M19.35 10.04A7.49 7.49 0 0 0 12 4C9.11 4 6.6 5.64 5.35 8.04A6 6 0 0 0 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z',
  buoy: 'M11 2h2v3h3l-1 4h2l2 9H5l2-9h2L8 5h3zM2 20h20v2H2z',
  balloon: 'M12 2a6 6 0 0 0-6 6c0 4 4 7 5 8h2c1-1 5-4 5-8a6 6 0 0 0-6-6zM11 17h2l-.5 2h-1zM11 20h2v2h-2z',
  radar: 'M12 2a10 10 0 1 0 10 10h-2a8 8 0 1 1-8-8zm0 4a6 6 0 1 0 6 6h-2a4 4 0 1 1-4-4zm0 4a2 2 0 1 0 2 2l6.3-6.3-1.4-1.4z',
  leaf: 'M6.05 8.05a7 7 0 0 0-.02 9.88c1.47-3.4 4.09-6.24 7.36-7.93A15.95 15.95 0 0 0 8.77 18.5c2.6 1.23 5.8.78 7.95-1.37C19.92 13.93 20 4 20 4S10.07 4.08 6.05 8.05z',
  radiation: 'M12 10a2 2 0 1 1 0 4 2 2 0 0 1 0-4zM10 9.2L6.5 3.2A10 10 0 0 0 2 12h7a3 3 0 0 1 1-2.8zM14 9.2a3 3 0 0 1 1 2.8h7a10 10 0 0 0-4.5-8.8zM13.5 14.6a3 3 0 0 1-3 0L7 20.7a10 10 0 0 0 10 0z',
  camera: 'M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z',
  radio: 'M3.24 6.15C2.51 6.43 2 7.17 2 8v12c0 1.1.89 2 2 2h16c1.11 0 2-.9 2-2V8c0-1.11-.89-2-2-2H8.3l8.26-3.34L15.88 1 3.24 6.15zM7 20c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm13-8h-2v-2h-2v2H4V8h16v4z',
  bus: 'M4 16c0 .88.39 1.67 1 2.22V20c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h8v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-6H6V6h12v5z',
  antenna: 'M12 5a3 3 0 0 0-1 5.83L7 22h2l1-3h4l1 3h2l-4-11.17A3 3 0 0 0 12 5zm-1.3 12l1.3-4 1.3 4zM6.3 3.3a8 8 0 0 0 0 11.4l1.4-1.4a6 6 0 0 1 0-8.6zm11.4 0l-1.4 1.4a6 6 0 0 1 0 8.6l1.4 1.4a8 8 0 0 0 0-11.4z',
  cable: 'M3 17c3 0 4-10 9-10s6 10 9 10v2c-4 0-5-10-9-10S7 19 3 19z',
  factory: 'M2 22V10l6 4V10l6 4V4h4v18z',
  news: 'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z',
  map: 'M20.5 3l-.16.03L15 5.1 9 3 3.36 4.9c-.21.07-.36.25-.36.48V20.5c0 .28.22.5.5.5l.16-.03L9 18.9l6 2.1 5.64-1.9c.21-.07.36-.25.36-.48V3.5c0-.28-.22-.5-.5-.5zM15 19l-6-2.11V5l6 2.11V19z',
};

// Kategori → renk ve simge; tür (kind) → simge (yoksa kategorinin)
export const CATS = {
  air: { color: '#38bdf8', icon: 'plane' }, sea: { color: '#2dd4bf', icon: 'ship' }, space: { color: '#a78bfa', icon: 'sat' },
  natural: { color: '#fb923c', icon: 'quake' }, weather: { color: '#60a5fa', icon: 'cloud' }, environment: { color: '#4ade80', icon: 'leaf' },
  camera: { color: '#f472b6', icon: 'camera' }, radio: { color: '#facc15', icon: 'radio' }, ground: { color: '#fdba74', icon: 'bus' },
  basemap: { color: '#94a3b8', icon: 'map' }, ham: { color: '#e879f9', icon: 'antenna' }, infra: { color: '#cbd5e1', icon: 'cable' },
  news: { color: '#f87171', icon: 'news' }, other: { color: '#e2e8f0', icon: 'pin' },
};
export const KIND_ICON = {
  aircraft: 'plane', vessel: 'ship', warning: 'warning', satellite: 'sat', iss: 'iss', aurora: 'aurora', quake: 'quake', fire: 'fire',
  disaster: 'warning', event: 'pin', volcano: 'volcano', lightning: 'bolt', metar: 'cloud', buoy: 'buoy', sonde: 'balloon', radar: 'radar',
  forecast: 'cloud', alert: 'warning', airquality: 'leaf', radiation: 'radiation', imagery: 'map', camera: 'camera', radio: 'radio',
  transit: 'bus', bike: 'bus', aprs: 'antenna', spot: 'antenna', cable: 'cable', plant: 'factory', cell: 'antenna', internet: 'globe', news: 'news',
};
export const KIND_COLOR = { quake: '#f43f5e', fire: '#f97316', volcano: '#ef4444', iss: '#c4b5fd', disaster: '#fbbf24' };

export function iconOf(kind, cat) { return KIND_ICON[kind] || CATS[cat]?.icon || 'pin'; }
export function colorOf(kind, cat) { return KIND_COLOR[kind] || CATS[cat]?.color || CATS.other.color; }

export function svgIcon(name, cls = '') {
  const ns = 'http://www.w3.org/2000/svg';
  const s = document.createElementNS(ns, 'svg');
  s.setAttribute('viewBox', '0 0 24 24');
  if (cls) s.setAttribute('class', cls);
  const p = document.createElementNS(ns, 'path');
  p.setAttribute('d', PATHS[name] || PATHS.pin);
  s.append(p);
  return s;
}

// Harita simgesi: koyu cam disk + renkli halka + renkli glif (style 'disc') ya da yalnız glif + koyu kontur (style 'bare'; uçak — yöne döner)
export function mapIcon(name, color, { style = 'disc', size = 26, ratio = 2 } = {}) {
  const px = Math.round(size * ratio);
  const c = document.createElement('canvas');
  c.width = c.height = px;
  const g = c.getContext('2d');
  const path = new Path2D(PATHS[name] || PATHS.pin);
  if (style === 'disc') {
    const r = px / 2 - ratio * 1.5;
    g.beginPath(); g.arc(px / 2, px / 2, r, 0, Math.PI * 2);
    g.fillStyle = 'rgba(8,12,22,0.86)'; g.fill();
    g.lineWidth = ratio * 1.6; g.strokeStyle = color; g.stroke();
    const s = (px * 0.58) / 24;
    g.save(); g.translate(px / 2 - 12 * s, px / 2 - 12 * s); g.scale(s, s);
    g.fillStyle = color; g.fill(path); g.restore();
  } else {
    const s = (px * 0.9) / 24;
    g.save(); g.translate(px / 2 - 12 * s, px / 2 - 12 * s); g.scale(s, s);
    g.lineJoin = 'round'; g.lineWidth = 2.4; g.strokeStyle = 'rgba(5,8,15,0.9)'; g.stroke(path);
    g.fillStyle = color; g.fill(path); g.restore();
  }
  return { width: px, height: px, data: new Uint8Array(g.getImageData(0, 0, px, px).data.buffer) };
}
