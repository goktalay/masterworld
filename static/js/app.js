// MASTERWORLD ön yüz girişi: küre, katman paneli, arama, kartlar, radyo çalar, isteğe bağlı üyelik, ayarların saklanması.
import { createMap, buildStyle, BASES } from './map.js';
import { Layers } from './layers.js';
import { CATS, colorOf, iconOf, svgIcon } from './icons.js';
import { apply, fmtNum, getLang, LANG_NAMES, LANGS, pickLang, setLang, t } from './i18n.js';
import * as S from './settings.js';
import { closeCard, createPlayer, h, openCard, weatherCard } from './cards.js';
import { initAuth } from './auth.js';
import { createAnalytics } from './analytics.js';

const $ = id => document.getElementById(id);
const CAT_ORDER = ['air', 'sea', 'space', 'natural', 'weather', 'environment', 'camera', 'radio', 'ground', 'ham', 'infra', 'news', 'basemap', 'other'];
let map, layers, defs = [], meta, analytics = { track() {} }, auth, player;
const catState = {};

async function boot() {
  const splash = h('div', { class: 'splash' }, svgUse('logo'));
  document.body.append(splash);
  try { meta = await (await fetch('/api/meta')).json(); } catch { meta = { mt_url: 'https://mastertool.download', mt_app: 'mw', ga_id: '' }; }
  const st = S.init(meta);
  await setLang(pickLang(st.lang));
  map = await createMap($('map'), { base: st.base, view: st.view, labels: st.labels !== false });
  player = createPlayer({ volume: st.volume ?? 0.8, onVolume: v => S.set({ volume: v }), onEvent: (n, p) => analytics.track(n, p) });
  layers = new Layers(map, { onSelect, onHover, onCounts: drawCounts, onStatus: () => {} });
  window.__mw = { map, layers };   // tanılama ve ekran görüntüsü testleri
  await new Promise(r => (map.loaded() ? r() : map.once('load', r)));
  document.body.classList.remove('booting');
  splash.classList.add('out'); setTimeout(() => splash.remove(), 1000);
  if (!st.view) map.easeTo({ center: [30, 28], zoom: innerWidth < 720 ? 1.3 : 1.9, duration: 2500 });
  layers._reattach();
  await loadLayers();
  ui();
  auth = initAuth({ meta, t, onLogin, onLogout, onEvent: (n, p) => analytics.track(n, p) });
  if (S.token()) onLogin(null).catch(() => {});
  analytics = createAnalytics({ gaId: meta.ga_id || '', t, privacyHref: '/gizlilik' });
  setInterval(drawStatus, 5000);
  addEventListener('pagehide', () => S.flush());
}

function svgUse(id) {
  const ns = 'http://www.w3.org/2000/svg';
  const s = document.createElementNS(ns, 'svg'); s.setAttribute('viewBox', '0 0 32 32');
  const u = document.createElementNS(ns, 'use'); u.setAttribute('href', `/img/icons.svg#${id}`); s.append(u);
  return s;
}

// ---------- katmanlar ----------
async function loadLayers() {
  let d = { categories: [], catalog: [] };
  try { d = await (await fetch('/api/layers')).json(); } catch { /* sunucu yok */ }
  layers.setDefs(d.categories);
  defs = d.categories.flatMap(c => c.sources.map(s => ({ ...s, category: s.category || c.key })));
  renderPanel(d);
  applyLayerSettings();
}

function applyLayerSettings() {
  const st = S.get();
  for (const s of defs) {
    if (s.mode === 'point') continue;
    const on = st.layers?.[s.slug] ?? s.default_on;
    if (on !== layers.isOn(s.slug)) layers.set(s.slug, on);
    const cb = document.querySelector(`input[data-slug="${s.slug}"]`);
    if (cb) cb.checked = !!on;
  }
  drawAttrib();
}

function renderPanel(d) {
  const byCat = {};
  for (const s of defs) (byCat[s.category] ||= []).push(s);
  const cats = Object.keys(byCat).sort((a, b) => CAT_ORDER.indexOf(a) - CAT_ORDER.indexOf(b));
  $('cats').replaceChildren(...cats.map(c => {
    const color = CATS[c]?.color || CATS.other.color;
    const ico = h('div', { class: 'cat-ico' }, svgIcon(CATS[c]?.icon || 'pin'));
    ico.style.setProperty('--c', color);
    const count = h('span', { class: 'cat-count', id: `cnt-${c}` });
    const el = h('div', { class: 'cat' + (catState[c] ?? (c === 'air' || c === 'camera' || c === 'radio') ? ' open' : '') },
      h('div', { class: 'cat-head', role: 'button', tabindex: 0, onclick: () => { el.classList.toggle('open'); catState[c] = el.classList.contains('open'); },
        onkeydown: e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.currentTarget.click(); } } },
      ico, h('span', { class: 'cat-name' }, t(`cat.${c}`)), count, svgIcon('chevron', 'cat-chev')),
      h('div', { class: 'cat-body' }, byCat[c].map(s => srcRow(s, color))));
    return el;
  }));
  const cat = d.catalog || [];
  $('catalog').replaceChildren(...cat.map(s => h('li', {}, h('b', {}, s.name), ' · ', h('span', { class: 'muted' }, t(`cat.${s.category}`)),
    s.reason === 'key_missing' ? h('span', { class: 'badge key' }, t('badge.key')) : null,
    s.noncommercial ? h('span', { class: 'badge nc' }, t('badge.nc')) : null,
    s.desc ? h('div', { class: 'muted' }, s.desc) : null)));
  document.querySelector('.catalog').hidden = !cat.length;
}

function srcRow(s, color) {
  const sw = h('label', { class: 'sw' }, h('input', { type: 'checkbox', 'data-slug': s.slug, 'aria-label': s.name, disabled: s.mode === 'point' ? true : null,
    onchange: e => { layers.set(s.slug, e.target.checked); S.set({ layers: { ...S.get().layers, [s.slug]: e.target.checked } }); drawAttrib();
      analytics.track('layer_toggle', { layer: s.slug, on: e.target.checked ? 1 : 0 }); } }), h('span', {}));
  sw.style.setProperty('--c', color);
  return h('div', { class: 'src', id: `src-${s.slug}` }, sw,
    h('div', { class: 'src-main' },
      h('div', { class: 'src-name' }, s.name, s.noncommercial ? h('span', { class: 'badge nc', title: t('badge.nc_t') }, t('badge.nc')) : null,
        s.attribution_required ? h('span', { class: 'badge att', title: t('badge.att_t') }, t('badge.att')) : null),
      s.desc ? h('div', { class: 'src-desc' }, s.desc) : null,
      h('div', { class: 'src-meta' }, s.mode === 'point' ? h('span', {}, t('src.point_hint')) : h('span', { class: 'n', id: `n-${s.slug}` }), h('span', { id: `e-${s.slug}` }))));
}

function drawCounts(metaMap) {
  const per = {};
  let live = 0;
  for (const s of defs) {
    const m = metaMap.get(s.slug);
    const row = $(`src-${s.slug}`);
    if (!row) continue;
    row.classList.toggle('loading', !!m?.loading && m.n == null);
    const n = $(`n-${s.slug}`), e = $(`e-${s.slug}`);
    if (n) n.textContent = layers.isOn(s.slug) && m?.n != null ? `${fmtNum(m.n)}${m.truncated ? '+' : ''}` : '';
    if (e) { e.className = m?.error ? 'err' : ''; e.textContent = !layers.isOn(s.slug) ? '' : m?.error ? t('src.unavailable') : m?.stale ? t('src.stale') : ''; }
    if (layers.isOn(s.slug)) { live++; per[s.category] = (per[s.category] || 0) + (m?.n || 0); }
  }
  for (const c of Object.keys(CATS)) { const el = $(`cnt-${c}`); if (el) el.textContent = per[c] ? fmtNum(per[c]) : ''; }
  $('live-count').textContent = t('layers.live', { n: live });
  drawStatus();
}

function drawStatus() {
  if (!layers) return;
  let n = 0, last = 0, err = 0;
  for (const [slug, m] of layers.meta) { if (!layers.isOn(slug)) continue; n += m.n || 0; last = Math.max(last, m.at || 0); if (m.error) err++; }
  const live = document.querySelector('.live');
  live.classList.toggle('warn', err > 0);
  $('status-text').textContent = t('status', { n: fmtNum(n), s: last ? Math.max(0, Math.round(Date.now() / 1000 - last)) : '—' });
}

function drawAttrib() {
  const b = BASES[S.get().base] || BASES.dark;
  const parts = [h('span', {}, b.attrib)];
  const seen = new Set();
  for (const s of defs) {
    if (!layers.isOn(s.slug) && s.mode !== 'point') continue;
    const a = s.attribution || s.name;
    if (seen.has(a)) continue;
    seen.add(a);
    parts.push(' · ', /^https:\/\//.test(s.attribution_url || '') ? h('a', { href: s.attribution_url, target: '_blank', rel: 'noopener noreferrer' }, a) : h('span', {}, a));
  }
  $('attrib').replaceChildren(...parts);
}

// ---------- seçim, ipucu ----------
function onSelect(def, it, lngLat) {
  if (!def || !it) { closeCard(); layers.select(null); return; }
  openCard(def, it, { player, onClosed: () => layers.select(null) });
  analytics.track('select_item', { kind: def.kind });
}

const hover = $('hover');
function onHover(info, ev) {
  if (!info || !ev || matchMedia('(hover: none)').matches) { hover.hidden = true; return; }
  hover.replaceChildren(info.cluster ? `${info.title} ` : info.title, h('i', {}, info.cluster ? `· ${info.sub || ''}` : info.sub || ''));
  hover.style.left = `${ev.clientX}px`; hover.style.top = `${ev.clientY}px`;
  hover.hidden = false;
}

async function weatherAt(lngLat) {
  const d = defs.find(s => s.mode === 'point');
  if (!d) return;
  try {
    const r = await fetch(`/api/data/${d.slug}?lat=${lngLat.lat.toFixed(3)}&lon=${lngLat.lng.toFixed(3)}`);
    if (!r.ok) throw new Error();
    weatherCard(d, await r.json(), lngLat);
    analytics.track('weather_here', {});
  } catch { /* kaynak yok */ }
}

// ---------- arayüz ----------
function ui() {
  const panel = $('panel');
  const st = S.get();
  if (st.panel === false || (st.panel == null && innerWidth < 720)) panel.classList.add('closed');
  const togglePanel = force => { const open = force ?? panel.classList.contains('closed'); panel.classList.toggle('closed', !open); $('btn-layers').classList.toggle('on', open); S.set({ panel: open }); };
  $('btn-layers').classList.toggle('on', !panel.classList.contains('closed'));
  $('btn-layers').addEventListener('click', () => togglePanel());
  $('panel-close').addEventListener('click', () => togglePanel(false));

  // Altlık menüsü
  const menu = $('basemenu');
  const drawMenu = () => {
    const cur = S.get().base;
    const lang = h('select', { class: 'lang', 'aria-label': 'Language', onchange: async e => { await setLang(e.target.value); S.set({ lang: e.target.value }); relabel(); } },
      LANGS.map(l => h('option', { value: l, selected: l === getLang() ? true : null }, LANG_NAMES[l])));
    menu.replaceChildren(...Object.entries(BASES).map(([k, b]) => h('button', { class: k === cur ? 'on' : '', onclick: () => setBase(k) },
      h('span', { class: `thumb ${b.thumb}` }), h('span', { class: 'lbl' }, t(b.label)))),
    h('label', { class: 'opt' }, h('input', { type: 'checkbox', checked: S.get().labels !== false ? true : null, onchange: e => { S.set({ labels: e.target.checked }); setBase(S.get().base, true); } }), t('base.labels')),
    h('label', { class: 'opt' }, svgIcon('globe'), lang));
  };
  $('btn-base').addEventListener('click', e => { e.stopPropagation(); drawMenu(); menu.hidden = !menu.hidden; $('btn-base').classList.toggle('on', !menu.hidden); });
  document.addEventListener('click', e => { if (!menu.hidden && !menu.contains(e.target)) { menu.hidden = true; $('btn-base').classList.remove('on'); } });

  $('attrib').addEventListener('click', e => { if (!e.target.closest('a')) $('attrib').classList.toggle('open'); });

  // Konumum
  $('btn-locate').addEventListener('click', () => navigator.geolocation?.getCurrentPosition(p => map.flyTo({ center: [p.coords.longitude, p.coords.latitude], zoom: 9, duration: 2200 }),
    () => {}, { enableHighAccuracy: false, timeout: 8000 }));

  // Hesap
  $('btn-account').addEventListener('click', () => auth.open());

  // Arama
  const q = $('search'), res = $('search-results');
  let sel = -1, found = [];
  const draw = () => {
    found = layers.search(q.value);
    const layerHits = q.value.trim().length >= 2 ? defs.filter(s => s.name.toLocaleLowerCase().includes(q.value.trim().toLocaleLowerCase())).slice(0, 4) : [];
    if (!q.value.trim()) { res.hidden = true; return; }
    const rows = [
      ...layerHits.map(s => h('button', { onclick: () => { const cb = document.querySelector(`input[data-slug="${s.slug}"]`); if (cb && !cb.checked) cb.click(); $(`src-${s.slug}`)?.closest('.cat')?.classList.add('open'); togglePanel(true); res.hidden = true; } },
        colored(svgIcon('layers'), colorOf(s.kind, s.category)), h('span', {}, s.name), h('span', { class: 'r-sub' }, t('search.layer')))),
      ...found.map(({ def, it }, i) => h('button', { class: i === sel ? 'on' : '', onclick: () => { layers.focus(def, it); res.hidden = true; q.blur(); } },
        colored(svgIcon(iconOf(def.kind, def.category)), colorOf(def.kind, def.category)), h('span', {}, it.name || '—'), h('span', { class: 'r-sub' }, def.name)))];
    res.replaceChildren(...(rows.length ? rows : [h('div', { class: 'empty' }, t('search.none'))]));
    res.hidden = false;
  };
  q.addEventListener('input', () => { sel = -1; draw(); });
  q.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { sel = Math.min(found.length - 1, sel + 1); draw(); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { sel = Math.max(0, sel - 1); draw(); e.preventDefault(); }
    else if (e.key === 'Enter' && found[Math.max(0, sel)]) { const f = found[Math.max(0, sel)]; layers.focus(f.def, f.it); res.hidden = true; q.blur(); }
    else if (e.key === 'Escape') { q.value = ''; res.hidden = true; q.blur(); }
  });
  document.addEventListener('click', e => { if (!e.target.closest('.search')) res.hidden = true; });

  // Görünüm kaydı
  let vt = 0;
  map.on('moveend', () => { clearTimeout(vt); vt = setTimeout(() => { const c = map.getCenter(); S.set({ view: { lng: +c.lng.toFixed(4), lat: +c.lat.toFixed(4), zoom: +map.getZoom().toFixed(2), bearing: +map.getBearing().toFixed(1), pitch: +map.getPitch().toFixed(1) } }); }, 800); });
  // Sağ tık / uzun basış → bu noktada hava
  map.on('contextmenu', e => { e.preventDefault?.(); weatherAt(e.lngLat); });

  // Klavye
  document.addEventListener('keydown', e => {
    if (e.target.closest('input, textarea, select')) return;
    if (e.key === 'Escape') closeCard();
    else if (e.key === 'l' || e.key === 'L') togglePanel();
    else if (e.key === '/') { e.preventDefault(); q.focus(); }
  });
}

const colored = (el, c) => { el.style.color = c; return el; };

async function setBase(k, force) {
  if (!BASES[k]) return;
  if (!force && S.get().base === k) return;
  S.set({ base: k });
  map.setStyle(await buildStyle(k, { labels: S.get().labels !== false }), { diff: false });
  $('basemenu').querySelectorAll('button').forEach((b, i) => b.classList.toggle('on', Object.keys(BASES)[i] === k));
  drawAttrib();
  analytics.track('basemap', { base: k });
}

function relabel() {
  apply(document);
  loadLayersPanelOnly();
  drawCounts(layers.meta);
}
async function loadLayersPanelOnly() {
  try { const d = await (await fetch('/api/layers')).json(); renderPanel(d); for (const s of defs) { const cb = document.querySelector(`input[data-slug="${s.slug}"]`); if (cb) cb.checked = layers.isOn(s.slug); } } catch { /* */ }
}

// ---------- üyelik ----------
async function onLogin(user) {
  const btn = $('btn-account');
  try {
    const r = await S.pull();
    const u = user || r.user;
    auth.setUser(u);
    btn.querySelector('.dot').hidden = false;
    btn.title = u?.name || t('account.title');
    $('sync-state').textContent = t('account.synced_short');
    if (r.applied) {
      const st = S.get();
      if (st.lang && st.lang !== getLang()) { await setLang(st.lang); relabel(); }
      if (st.base) await setBase(st.base, true);
      if (st.view) map.flyTo({ center: [st.view.lng, st.view.lat], zoom: st.view.zoom, bearing: st.view.bearing, pitch: st.view.pitch, duration: 1600 });
      applyLayerSettings();
    }
  } catch {
    if (!S.token()) onLogout();
  }
}
function onLogout() {
  const btn = $('btn-account');
  btn.querySelector('.dot').hidden = true;
  btn.title = t('account.title');
  $('sync-state').textContent = t('account.local');
}
S.onSync(e => {
  const el = $('sync-state');
  if (e.state === 'signed_out') onLogout();
  else if (el) el.textContent = t(`sync.${e.state}`);
});

boot().catch(e => {
  console.error(e);
  document.body.classList.remove('booting');
  document.querySelector('.splash')?.remove();
  document.body.append(h('div', { class: 'noscript' }, t('err.webgl')));
});
