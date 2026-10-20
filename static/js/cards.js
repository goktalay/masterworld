// Tıklama kartları: kamera → canlı küçük önizleme (sunucu vekili /api/media, N sn'de bir), radyo → mini çalar, uçak / gemi / deprem / … → bilgi kartı.
import { colorOf, iconOf, svgIcon } from './icons.js';
import { ago, fmtNum, fmtTime, t } from './i18n.js';

export function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const c of kids.flat()) if (c != null && c !== false) e.append(c);
  return e;
}

const safeUrl = u => (typeof u === 'string' && /^https:\/\//.test(u) ? u : null);
const card = document.getElementById('card');
let timer = 0, onClose = null;

export function closeCard() {
  clearInterval(timer); timer = 0;
  card.hidden = true; card.classList.remove('big'); card.replaceChildren();
  const f = onClose; onClose = null; f?.();
}

function head(def, title, sub) {
  const ico = h('div', { class: 'cat-ico' }, svgIcon(iconOf(def?.kind, def?.category)));
  ico.style.setProperty('--c', colorOf(def?.kind, def?.category));
  return h('div', { class: 'card-head' }, ico, h('div', { class: 'card-title' }, h('b', {}, title || '—'), h('span', {}, sub || '')),
    h('button', { class: 'ibtn plain', 'aria-label': t('close'), onclick: closeCard }, svgIcon('close')));
}

function foot(def, extra = []) {
  const href = safeUrl(def?.attribution_url);
  return h('div', { class: 'card-foot' },
    h('span', {}, t('card.source'), ': ', href ? h('a', { href, target: '_blank', rel: 'noopener noreferrer' }, def.attribution || def.name) : (def?.attribution || def?.name || '')),
    def?.noncommercial ? h('span', { class: 'badge nc' }, t('badge.nc')) : null,
    h('span', { class: 'sp' }), ...extra);
}

function dl(rows) {
  const r = rows.filter(([, v]) => v != null && v !== '' && v !== '—');
  return r.length ? h('dl', {}, r.flatMap(([k, v]) => [h('dt', {}, k), h('dd', {}, v)])) : null;
}

const link = (url, label) => (safeUrl(url) ? h('a', { class: 'btn sm', href: url, target: '_blank', rel: 'noopener noreferrer' }, svgIcon('link'), label || t('card.open')) : null);
const coord = it => `${it.lat.toFixed(4)}, ${it.lon.toFixed(4)}`;

function show(...kids) {
  clearInterval(timer); timer = 0;
  card.replaceChildren(...kids);
  card.hidden = false;
}

export function openCard(def, it, { onClosed, player } = {}) {
  const prev = onClose; onClose = null; prev?.();
  onClose = onClosed || null;
  const k = def.kind, p = it.p || {};
  if (k === 'radio') { player.play(def, it); return closeCard(); }
  if (p.media === 'image') return cameraCard(def, it);
  if (k === 'aircraft') {
    const altFt = p.alt_ft ?? (it.alt != null ? it.alt / 0.3048 : null);
    return show(head(def, it.name || p.reg || p.hex, [p.type, p.desc].filter(Boolean).join(' · ') || t('kind.aircraft')),
      dl([[t('f.reg'), p.reg], [t('f.hex'), p.hex?.toUpperCase()], [t('f.alt'), p.ground ? t('f.ground') : altFt != null ? `${fmtNum(altFt)} ft · ${fmtNum(altFt * 0.3048)} m` : null],
        [t('f.speed'), it.spd != null ? `${fmtNum(it.spd)} kt · ${fmtNum(it.spd * 1.852)} km/h` : null], [t('f.heading'), it.hdg != null ? `${fmtNum(it.hdg)}°` : null],
        [t('f.vs'), p.vs_fpm != null ? `${fmtNum(p.vs_fpm)} ft/min` : null], [t('f.squawk'), p.squawk], [t('f.operator'), p.op], [t('f.pos'), coord(it)]]),
      foot(def, [link(p.hex ? `https://globe.adsb.lol/?icao=${encodeURIComponent(p.hex)}` : null, t('card.track'))]));
  }
  if (k === 'quake') {
    return show(head(def, p.mag != null ? `M ${Number(p.mag).toFixed(1)} · ${it.name}` : it.name, it.t ? `${ago(it.t)} · ${fmtTime(it.t)}` : ''),
      dl([[t('f.mag'), p.mag != null ? `${Number(p.mag).toFixed(1)} ${p.type || ''}` : null], [t('f.depth'), p.depth_km != null ? `${fmtNum(p.depth_km, 1)} km` : null],
        [t('f.felt'), p.felt], [t('f.tsunami'), p.tsunami ? t('yes') : null], [t('f.alert'), p.alert], [t('f.pos'), coord(it)]]),
      foot(def, [link(p.url)]));
  }
  if (k === 'satellite' || k === 'iss') {
    return show(head(def, it.name, k === 'iss' ? t('kind.iss') : (p.omm?.NORAD_CAT_ID ? `NORAD ${p.omm.NORAD_CAT_ID}` : t('kind.satellite'))),
      dl([[t('f.alt'), it.alt != null ? `${fmtNum(it.alt / 1000)} km` : p.alt_km != null ? `${fmtNum(p.alt_km)} km` : null],
        [t('f.speed'), p.vel_kmh != null ? `${fmtNum(p.vel_kmh)} km/h` : null], [t('f.incl'), p.omm ? `${fmtNum(p.omm.INCLINATION, 1)}°` : null],
        [t('f.period'), p.omm ? `${fmtNum(1440 / p.omm.MEAN_MOTION, 1)} min` : null], [t('f.epoch'), p.omm?.EPOCH?.slice(0, 16).replace('T', ' ')],
        [t('f.pos'), coord({ lat: it._lat ?? it.lat, lon: it._lon ?? it.lon })]]),
      p.omm ? h('p', { class: 'small muted card-note' }, t('card.track_hint')) : null,
      foot(def));
  }
  // Genel: p alanlarını okunur listele
  const rows = [];
  for (const [kk, v] of Object.entries(p)) {
    if (['url', 'media', 'omm', 'rank', 'color', 'stream', 'favicon', 'homepage'].includes(kk) || typeof v === 'object') continue;
    rows.push([t(`f.${kk}`) !== `f.${kk}` ? t(`f.${kk}`) : kk, typeof v === 'number' ? fmtNum(v, 2) : String(v)]);
  }
  if (it.t) rows.push([t('f.time'), `${fmtTime(it.t)} (${ago(it.t)})`]);
  if (it.lat != null && !it._line) rows.push([t('f.pos'), coord(it)]);
  return show(head(def, it.name, def.name), dl(rows.slice(0, 16)), foot(def, [link(p.url || p.homepage)]));
}

function cameraCard(def, it) {
  const img = h('img', { alt: it.name || '' });
  const ts = h('span', { class: 'ts' });
  const spin = h('div', { class: 'spinner' });
  const over = h('div', { class: 'msg-over', hidden: true }, t('card.cam_err'));
  const media = h('div', { class: 'card-media' }, spin, img, h('span', { class: 'live-tag' }, t('card.live')), ts, over);
  let first = true;
  const load = () => {
    const u = `/api/media/${encodeURIComponent(def.slug)}/${encodeURIComponent(it.id)}?t=${Math.floor(Date.now() / 15000)}`;
    const nx = new Image();
    if (!first) img.classList.add('fade');
    nx.onload = () => { img.src = nx.src; img.classList.remove('fade'); spin.hidden = true; over.hidden = true; ts.textContent = new Date().toLocaleTimeString(); first = false; };
    nx.onerror = () => { spin.hidden = true; if (first) over.hidden = false; img.classList.remove('fade'); };
    nx.src = u;
  };
  const big = h('button', { class: 'btn sm', onclick: () => card.classList.toggle('big') }, svgIcon('expand'), t('card.enlarge'));
  show(head(def, it.name, [it.p?.country, it.p?.road, def.name].filter(Boolean).join(' · ')), media,
    dl([[t('f.pos'), coord(it)], [t('f.desc'), it.p?.desc]]),
    foot(def, [big, link(it.p?.url || it.p?.page)]));
  load();
  timer = setInterval(load, Math.max(10, Number(it.p?.refresh_s) || 15) * 1000);
}

// Hava durumu (Open-Meteo, mode point): sağ tık / uzun basış
export function weatherCard(def, res, lngLat) {
  const d = res?.data || {};
  const cur = d.current || {};
  const hrs = d.hourly || {};
  const temps = (hrs.temperature_2m || []).slice(0, 24);
  let chart = null;
  if (temps.length > 2) {
    const mn = Math.min(...temps), mx = Math.max(...temps), W = 300, H = 60, sx = W / (temps.length - 1), sy = v => H - 6 - ((v - mn) / Math.max(1, mx - mn)) * (H - 16);
    const pts = temps.map((v, i) => `${(i * sx).toFixed(1)},${sy(v).toFixed(1)}`).join(' ');
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', `0 0 ${W} ${H + 10}`);
    svg.innerHTML = `<defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#38bdf8"/><stop offset="1" stop-color="#38bdf8" stop-opacity="0"/></linearGradient></defs>`
      + `<polygon class="ar" points="0,${H} ${pts} ${W},${H}"/><polyline class="ln" points="${pts}"/>`
      + `<text class="ax" x="0" y="${H + 9}">${Math.round(mn)}°</text><text class="ax" x="${W - 18}" y="${H + 9}">${Math.round(mx)}°</text>`;
    chart = h('div', { class: 'chart' }, svg);
  }
  const wc = cur.weather_code != null ? t(`wx.${cur.weather_code}`) : '';
  show(head(def, t('card.weather_here'), `${lngLat.lat.toFixed(2)}, ${lngLat.lng.toFixed(2)}`),
    h('div', { class: 'wx-now' }, h('b', {}, cur.temperature_2m != null ? `${Math.round(cur.temperature_2m)}°` : '—'), h('span', { class: 'muted' }, wc.startsWith('wx.') ? '' : wc)),
    chart,
    dl([[t('f.wind'), cur.wind_speed_10m != null ? `${fmtNum(cur.wind_speed_10m)} km/h · ${fmtNum(cur.wind_direction_10m)}°` : null],
      [t('f.humidity'), cur.relative_humidity_2m != null ? `%${fmtNum(cur.relative_humidity_2m)}` : null],
      [t('f.precip'), cur.precipitation != null ? `${fmtNum(cur.precipitation, 1)} mm` : null]]),
    foot(def));
}

// ---------- radyo mini çalar ----------
export function createPlayer({ onVolume, volume = 0.8, onEvent = () => {} }) {
  const root = document.getElementById('player');
  const audio = root.querySelector('#audio');
  const name = root.querySelector('#player-name'), sub = root.querySelector('#player-sub');
  const tog = root.querySelector('#player-toggle'), vol = root.querySelector('#player-vol');
  const setIcon = n => { tog.replaceChildren(svgIcon(n)); };
  audio.volume = vol.value = volume;
  let cur = null;
  const status = s => { root.classList.toggle('playing', s === 'playing'); root.classList.toggle('err', s === 'error'); setIcon(s === 'playing' || s === 'loading' ? 'pause' : 'play');
    if (s === 'error') sub.textContent = t('player.error'); else if (s === 'loading') sub.textContent = t('player.loading'); else if (cur) sub.textContent = cur.sub; };
  audio.addEventListener('playing', () => status('playing'));
  audio.addEventListener('pause', () => status('paused'));
  audio.addEventListener('waiting', () => status('loading'));
  audio.addEventListener('error', () => { if (cur) status('error'); });
  tog.addEventListener('click', () => { if (!cur) return; if (audio.paused) { status('loading'); audio.play().catch(() => status('error')); } else audio.pause(); });
  vol.addEventListener('input', () => { audio.volume = Number(vol.value); onVolume?.(audio.volume); });
  root.querySelector('#player-close').addEventListener('click', () => { audio.pause(); audio.removeAttribute('src'); audio.load(); cur = null; root.hidden = true; });
  return {
    play(def, it) {
      const url = safeUrl(it.p?.stream);
      if (!url) return;
      const p = it.p || {};
      cur = { sub: [p.country, p.codec && `${p.codec}${p.bitrate ? ` ${p.bitrate} kbps` : ''}`, (Array.isArray(p.tags) ? p.tags : String(p.tags || '').split(',')).filter(Boolean).slice(0, 3).join(', ')].filter(Boolean).join(' · ') };
      name.textContent = it.name || '—';
      root.hidden = false;
      audio.src = url;
      status('loading');
      audio.play().catch(() => status('error'));
      try { onEvent('radio_play', { station_country: p.countrycode || '' }); } catch { /* */ }
    },
  };
}
