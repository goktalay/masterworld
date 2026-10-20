// Katman yöneticisi: /api/layers tanımları → MapLibre kaynak/katmanları, yenileme döngüsü, kümeleme, seçim, üzerine gelme.
// Tüm veri masterworld sunucusundan (/api/data, /api/tile); istemci kaynaklara doğrudan gitmez.
import { colorOf, iconOf, mapIcon } from './icons.js';
import { elements, groundTrack, position } from './sat.js';

const P = 'mw-';
const GLOBAL_KINDS = new Set(['satellite', 'iss', 'cable', 'aurora', 'sonde']);   // görünüm alanından bağımsız istenir
const MOVERS = new Set(['aircraft', 'vessel']);                                    // yönlü simge + ölü hesap (dead reckoning)
const NO_CLUSTER = new Set(['aircraft', 'vessel', 'satellite', 'iss', 'quake', 'sonde', 'aurora', 'fire']);
const HEAT = new Set(['aurora']);
// isStyleLoaded() karolar yüklenene dek false döner; burada yalnız stil belgesinin yüklü olması gerekir
const styleReady = m => !!m.style?._loaded;
const SUFFIXES = ['-line', '-cl', '-cn', '-pt', '-pulse', '-heat', '-raster'];

export class Layers {
  constructor(map, { onSelect, onHover, onCounts, onStatus }) {
    this.map = map; this.onSelect = onSelect; this.onHover = onHover; this.onCounts = onCounts; this.onStatus = onStatus;
    this.defs = new Map(); this.visible = new Set(); this.items = new Map(); this.data = new Map(); this.meta = new Map();
    this.timers = new Map(); this.aborts = new Map(); this.sats = new Map(); this.sel = null;
    this.icons = new Set();
    this._moveT = 0;
    map.on('moveend', () => { clearTimeout(this._moveT); this._moveT = setTimeout(() => this._refetchOnMove(), 450); });
    map.on('style.load', () => this._reattach());
    this._tick = setInterval(() => this._animate(), 1000);
    this._pulse();
    this._bindPointer();
  }

  setDefs(categories) {
    for (const c of categories) for (const s of c.sources) this.defs.set(s.slug, { ...s, category: s.category || c.key });
  }

  isOn(slug) { return this.visible.has(slug); }

  set(slug, on) {
    const d = this.defs.get(slug);
    if (!d) return;
    if (on) {
      this.visible.add(slug);
      this._ensure(d);
      this._schedule(d, 0);
    } else {
      this.visible.delete(slug);
      clearTimeout(this.timers.get(slug)); this.timers.delete(slug);
      this.aborts.get(slug)?.abort();
      this._remove(slug);
      this.items.delete(slug); this.data.delete(slug); this.meta.delete(slug);
      if (this.sel?.slug === slug) this.select(null);
      this._counts();
    }
  }

  // ---------- veri ----------
  _bbox() {
    const b = this.map.getBounds();
    let w = b.getWest(), e = b.getEast(), s = b.getSouth(), n = b.getNorth();
    if (this.map.getZoom() < 2.6 || e - w > 300) return [-180, -90, 180, 90];
    const pw = (e - w) * 0.25, ph = (n - s) * 0.25;
    return [Math.max(-180, w - pw), Math.max(-90, s - ph), Math.min(180, e + pw), Math.min(90, n + ph)];
  }

  // Hücreli kaynaklar (uçak, METAR …): uzak görünümde tüm dünya yerine haritanın ortasındaki pencere — sunucu hücreleri merkezden sıralar
  _focusBox() {
    const b = this._bbox();
    if (b[2] - b[0] < 120) return b;
    const c = this.map.getCenter();
    return [Math.max(-180, c.lng - 30), Math.max(-85, c.lat - 18), Math.min(180, c.lng + 30), Math.min(85, c.lat + 18)];
  }

  _refetchOnMove() {
    for (const slug of this.visible) {
      const d = this.defs.get(slug);
      if (d.mode === 'tile' || GLOBAL_KINDS.has(d.kind) || d.mode === 'point') continue;
      this._schedule(d, 0);
    }
  }

  _schedule(d, ms) {
    clearTimeout(this.timers.get(d.slug));
    if (d.mode === 'tile' || d.mode === 'point') return;
    this.timers.set(d.slug, setTimeout(() => this._load(d), ms));
  }

  async _load(d) {
    if (!this.visible.has(d.slug)) return;
    this.aborts.get(d.slug)?.abort();
    const ac = new AbortController();
    this.aborts.set(d.slug, ac);
    const m = this.meta.get(d.slug) || {};
    this.meta.set(d.slug, { ...m, loading: true });
    this._counts();
    const q = GLOBAL_KINDS.has(d.kind) ? '' : `?bbox=${(d.mode === 'bbox' ? this._focusBox() : this._bbox()).map(v => v.toFixed(3)).join(',')}`;
    let next = Math.max(5, d.refresh_s || 60) * 1000;
    try {
      const r = await fetch(`/api/data/${d.slug}${q}`, { signal: ac.signal });
      if (r.status === 429) next = Math.max(next, (parseInt(r.headers.get('Retry-After') || '30', 10) || 30) * 1000);
      if (!r.ok) throw new Error(r.status === 503 ? 'unavailable' : `http_${r.status}`);
      const res = await r.json();
      this._ingest(d, res);
      this.meta.set(d.slug, { n: res.items.length, at: res.fetched_at, stale: !!res.stale, truncated: !!res.truncated, error: null });
    } catch (e) {
      if (e.name === 'AbortError') return;
      this.meta.set(d.slug, { ...(this.meta.get(d.slug) || {}), loading: false, error: e.message === 'unavailable' ? 'unavailable' : 'error' });
      next = Math.min(next * 2, 120000);
    }
    this._counts();
    if (this.visible.has(d.slug)) this._schedule(d, next);
  }

  _ingest(d, res) {
    const map = new Map();
    const now = Date.now();
    for (const it of res.items) {
      it._slug = d.slug; it._kind = d.kind; it._cat = d.category; it._at = now;
      map.set(String(it.id), it);
      if (d.kind === 'satellite' && it.p?.omm) {
        const el = elements(it.p.omm);
        if (el) this.sats.set(`${d.slug}|${it.id}`, el);
      }
    }
    this.items.set(d.slug, map);
    this.data.set(d.slug, res);
    if (d.kind === 'satellite') this._propagate(d.slug);
    this._render(d);
    if (this.sel?.slug === d.slug) {
      const it = map.get(String(this.sel.id));
      if (it) { this.sel.item = it; this._selDraw(); }
    }
  }

  _feature(it) {
    const p = it.p || {};
    return { type: 'Feature', id: undefined, geometry: { type: 'Point', coordinates: [it._lon ?? it.lon, it._lat ?? it.lat] },
      properties: { _slug: it._slug, _id: String(it.id), name: it.name || '', hdg: it.hdg ?? 0, alt: it.alt ?? null,
        mag: p.mag ?? null, t: it.t ?? null, rank: p.rank ?? p.votes ?? 0, ground: p.ground ? 1 : 0, color: p.color || null } };
  }

  _render(d) {
    const src = this.map.getSource(P + d.slug);
    if (!src) return;
    const its = [...(this.items.get(d.slug) || new Map()).values()];
    const feats = its.map(it => this._feature(it));
    if (d.kind === 'cable') {
      const lines = (this.data.get(d.slug)?.lines || []).map(l => ({ type: 'Feature', geometry: { type: 'LineString', coordinates: l.coords },
        properties: { _slug: d.slug, _id: String(l.id), name: l.name || '', color: l.p?.color || null } }));
      this.map.getSource(P + d.slug + '-lines')?.setData({ type: 'FeatureCollection', features: lines });
    }
    src.setData({ type: 'FeatureCollection', features: feats });
  }

  // ---------- harita kaynak/katmanları ----------
  _icon(kind, cat, bare) {
    const id = `${P}${bare ? 'b' : 'd'}-${kind}`;
    if (!this.icons.has(id) || !this.map.hasImage(id)) {
      if (!this.map.hasImage(id)) this.map.addImage(id, mapIcon(iconOf(kind, cat), colorOf(kind, cat), bare ? { style: 'bare', size: 22 } : {}), { pixelRatio: 2 });
      this.icons.add(id);
    }
    return id;
  }

  _beforeId() {
    // Veri katmanları altlık yazılarının ÜSTÜNDE (her zaman okunur); seçim halesi en üstte
    return this.map.getLayer(P + 'sel-halo') ? P + 'sel-halo' : undefined;
  }

  _ensure(d) {
    if (!styleReady(this.map)) return;   // stil değişiyor: 'style.load' → _reattach görünür katmanları ekler
    const map = this.map, id = P + d.slug, color = colorOf(d.kind, d.category), before = this._beforeId();
    if (map.getSource(id) || (d.mode === 'tile' && map.getSource(id + '-tiles'))) return;
    if (d.mode === 'tile') {
      map.addSource(id + '-tiles', { type: 'raster', tiles: [`${location.origin}/api/tile/${d.slug}/{z}/{x}/{y}.png`], tileSize: 256, maxzoom: d.max_zoom || 7,
        attribution: d.attribution });
      const firstSym = map.getStyle().layers.find(l => l.type === 'symbol')?.id;
      map.addLayer({ id: id + '-raster', type: 'raster', source: id + '-tiles', paint: { 'raster-opacity': 0.62, 'raster-fade-duration': 400 } }, firstSym);
      return;
    }
    const cluster = !NO_CLUSTER.has(d.kind);
    map.addSource(id, { type: 'geojson', data: { type: 'FeatureCollection', features: [] }, ...(cluster ? { cluster: true, clusterRadius: 46, clusterMaxZoom: 11 } : {}) });
    if (d.kind === 'cable') {
      map.addSource(id + '-lines', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({ id: id + '-line', type: 'line', source: id + '-lines', layout: { 'line-cap': 'round' },
        paint: { 'line-color': ['coalesce', ['get', 'color'], color], 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 0.8, 6, 2.2], 'line-opacity': 0.75 } }, before);
    }
    if (cluster) {
      map.addLayer({ id: id + '-cl', type: 'circle', source: id, filter: ['has', 'point_count'],
        paint: { 'circle-color': color, 'circle-opacity': 0.22, 'circle-stroke-color': color, 'circle-stroke-width': 1.5, 'circle-stroke-opacity': 0.9,
          'circle-radius': ['interpolate', ['linear'], ['get', 'point_count'], 2, 13, 50, 18, 500, 26, 5000, 34] } }, before);
      map.addLayer({ id: id + '-cn', type: 'symbol', source: id, filter: ['has', 'point_count'],
        layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-font': ['Noto Sans Regular'], 'text-size': 11.5, 'text-allow-overlap': true },
        paint: { 'text-color': '#fff', 'text-halo-color': 'rgba(0,0,0,.6)', 'text-halo-width': 1 } }, before);
    }
    const unc = cluster ? ['!', ['has', 'point_count']] : ['all'];
    if (d.kind === 'quake') {
      const age = ['-', ['/', ['number', ['get', 't'], 0], 1], Math.floor(Date.now() / 1000)];
      map.addLayer({ id: id + '-pt', type: 'circle', source: id,
        paint: { 'circle-radius': ['interpolate', ['exponential', 1.6], ['coalesce', ['get', 'mag'], 1], 0, 2.5, 3, 5, 5, 10, 7, 20, 9, 32],
          'circle-color': ['interpolate', ['linear'], ['coalesce', ['get', 'mag'], 1], 1, '#fde047', 3, '#fb923c', 5, '#f43f5e', 7, '#be123c'],
          'circle-opacity': ['interpolate', ['linear'], age, -86400 * 2, 0.35, -3600, 0.75, 0, 0.95],
          'circle-stroke-color': '#fff', 'circle-stroke-width': 0.6, 'circle-stroke-opacity': 0.5, 'circle-blur': 0.05 } }, before);
      map.addLayer({ id: id + '-pulse', type: 'circle', source: id, filter: ['>', ['coalesce', ['get', 't'], 0], Math.floor(Date.now() / 1000) - 7200],
        paint: { 'circle-radius': 10, 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-color': '#f43f5e', 'circle-stroke-width': 1.5, 'circle-stroke-opacity': 0.8 } }, before);
    } else if (HEAT.has(d.kind)) {
      map.addLayer({ id: id + '-heat', type: 'heatmap', source: id, maxzoom: 9,
        paint: { 'heatmap-weight': ['interpolate', ['linear'], ['get', 'rank'], 0, 0, 100, 1], 'heatmap-intensity': 0.9, 'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 8, 6, 28],
          'heatmap-opacity': 0.55, 'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'], 0, 'rgba(0,0,0,0)', 0.3, 'rgba(16,185,129,.5)', 0.6, '#34d399', 0.85, '#a3e635', 1, '#f0abfc'] } }, before);
    } else if (d.kind === 'fire') {
      map.addLayer({ id: id + '-heat', type: 'heatmap', source: id, maxzoom: 7,
        paint: { 'heatmap-weight': ['interpolate', ['linear'], ['get', 'rank'], 0, 0.2, 50, 1], 'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 4, 6, 18],
          'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 5, 0.8, 7, 0],
          'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'], 0, 'rgba(0,0,0,0)', 0.3, 'rgba(249,115,22,.5)', 0.7, '#f97316', 1, '#fde047'] } }, before);
      map.addLayer({ id: id + '-pt', type: 'circle', source: id, minzoom: 5,
        paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 5, 2, 10, 5], 'circle-color': '#f97316', 'circle-blur': 0.4, 'circle-opacity': 0.9 } }, before);
    } else if (MOVERS.has(d.kind)) {
      map.addLayer({ id: id + '-pt', type: 'symbol', source: id,
        layout: { 'icon-image': this._icon(d.kind, d.category, true), 'icon-rotate': ['get', 'hdg'], 'icon-rotation-alignment': 'map', 'icon-allow-overlap': true,
          'icon-ignore-placement': true, 'icon-size': ['interpolate', ['linear'], ['zoom'], 1, 0.55, 6, 0.85, 10, 1.1],
          'text-field': ['step', ['zoom'], '', 7, ['get', 'name']], 'text-font': ['Noto Sans Regular'], 'text-size': 10.5, 'text-offset': [0, 1.35], 'text-anchor': 'top', 'text-optional': true },
        paint: { 'icon-opacity': ['case', ['==', ['get', 'ground'], 1], 0.45, 1], 'text-color': '#cfe8ff', 'text-halo-color': 'rgba(0,0,0,.8)', 'text-halo-width': 1.2 } }, before);
    } else {
      const sat = d.kind === 'satellite';
      map.addLayer({ id: id + '-pt', type: 'symbol', source: id, filter: unc,
        layout: { 'icon-image': this._icon(d.kind, d.category, false), 'icon-allow-overlap': sat || d.kind === 'iss', 'icon-ignore-placement': sat,
          'icon-size': sat ? ['interpolate', ['linear'], ['zoom'], 0, 0.42, 4, 0.6] : d.kind === 'iss' ? 1.15 : ['interpolate', ['linear'], ['zoom'], 1, 0.7, 8, 0.95],
          'symbol-sort-key': ['-', 0, ['get', 'rank']],
          'text-field': ['step', ['zoom'], '', d.kind === 'iss' ? 0 : 9, ['get', 'name']], 'text-font': ['Noto Sans Regular'], 'text-size': 11, 'text-offset': [0, 1.4],
          'text-anchor': 'top', 'text-optional': true },
        paint: { 'text-color': '#e2e8f0', 'text-halo-color': 'rgba(0,0,0,.85)', 'text-halo-width': 1.2 } }, before);
    }
    if (this.items.has(d.slug)) this._render(d);
  }

  _layerIds(slug) {   // getStyle() tüm stili serileştirir (pahalı) → bilinen son ekler
    return SUFFIXES.map(s => P + slug + s).filter(l => this.map.getLayer(l));
  }

  _remove(slug) {
    for (const l of this._layerIds(slug)) this.map.removeLayer(l);
    for (const s of [P + slug, P + slug + '-lines', P + slug + '-tiles']) if (this.map.getSource(s)) this.map.removeSource(s);
    for (const k of [...this.sats.keys()]) if (k.startsWith(slug + '|')) this.sats.delete(k);
  }

  interactive() {
    const ids = [];
    for (const slug of this.visible) for (const s of ['-pt', '-cl', '-line']) if (this.map.getLayer(P + slug + s)) ids.push(P + slug + s);
    return ids;
  }

  _reattach() {
    this.icons.clear();
    this._selLayers();
    for (const slug of this.visible) this._ensure(this.defs.get(slug));
    this._selDraw();
  }

  // ---------- canlandırma ----------
  _animate() {
    if (document.hidden) return;
    const now = Date.now();
    for (const slug of this.visible) {
      const d = this.defs.get(slug);
      if (d.kind === 'satellite') { this._propagate(slug); this._render(d); continue; }
      if (!MOVERS.has(d.kind)) continue;
      const its = this.items.get(slug);
      if (!its || its.size > 4000) continue;
      for (const it of its.values()) {
        const dt = Math.min(30, (now - it._at) / 1000);
        if (!it.spd || it.hdg == null || it.p?.ground || dt <= 0) { it._lat = it.lat; it._lon = it.lon; continue; }
        const dist = it.spd * 0.514444 * dt;   // kt → m/s
        const h = it.hdg * Math.PI / 180;
        it._lat = it.lat + (dist * Math.cos(h)) / 111320;
        it._lon = it.lon + (dist * Math.sin(h)) / (111320 * Math.max(0.05, Math.cos(it.lat * Math.PI / 180)));
      }
      this._render(d);
    }
    if (this.sel) this._selDraw();
  }

  _propagate(slug) {
    const its = this.items.get(slug);
    if (!its) return;
    const now = Date.now();
    for (const it of its.values()) {
      const el = this.sats.get(`${slug}|${it.id}`);
      if (!el) continue;
      const p = position(el, now);
      it._lat = p.lat; it._lon = p.lon; it.alt = Math.round(p.alt * 1000);
    }
  }

  _pulse() {   // son 2 saatteki depremlerin halkası
    const step = ts => {
      const r = (ts % 2000) / 2000;
      for (const slug of this.visible) {
        const l = P + slug + '-pulse';
        if (this.map.getLayer(l)) {
          this.map.setPaintProperty(l, 'circle-radius', 6 + r * 26);
          this.map.setPaintProperty(l, 'circle-stroke-opacity', 0.85 * (1 - r));
        }
      }
      this._raf = requestAnimationFrame(step);
    };
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches) this._raf = requestAnimationFrame(step);
  }

  // ---------- seçim ----------
  _selLayers() {
    const map = this.map;
    if (!styleReady(map)) return;
    if (!map.getSource(P + 'sel')) map.addSource(P + 'sel', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    if (!map.getSource(P + 'sel-track')) map.addSource(P + 'sel-track', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    if (!map.getLayer(P + 'sel-track')) map.addLayer({ id: P + 'sel-track', type: 'line', source: P + 'sel-track',
      paint: { 'line-color': '#c4b5fd', 'line-width': 1.6, 'line-dasharray': [2, 2], 'line-opacity': 0.85 } });
    if (!map.getLayer(P + 'sel-halo')) map.addLayer({ id: P + 'sel-halo', type: 'circle', source: P + 'sel',
      paint: { 'circle-radius': 17, 'circle-color': 'rgba(56,189,248,0.12)', 'circle-stroke-color': '#7dd3fc', 'circle-stroke-width': 2 } });
  }

  select(sel) {
    this.sel = sel;
    this._selDraw();
  }

  _selDraw() {
    const s = this.map.getSource(P + 'sel'), tr = this.map.getSource(P + 'sel-track');
    if (!s) return;
    const it = this.sel?.item;
    s.setData({ type: 'FeatureCollection', features: it && it.lat != null ? [{ type: 'Feature', geometry: { type: 'Point', coordinates: [it._lon ?? it.lon, it._lat ?? it.lat] }, properties: {} }] : [] });
    let lines = [];
    const el = it && this.sats.get(`${this.sel.slug}|${it.id}`);
    if (el) lines = groundTrack(el, Date.now());
    tr?.setData({ type: 'FeatureCollection', features: lines.map(c => ({ type: 'Feature', geometry: { type: 'LineString', coordinates: c }, properties: {} })) });
  }

  // ---------- işaretçi ----------
  _bindPointer() {
    const map = this.map;
    let hovered = null;
    map.on('mousemove', e => {
      const ids = this.interactive();
      const f = ids.length ? map.queryRenderedFeatures(e.point, { layers: ids })[0] : null;
      map.getCanvas().style.cursor = f ? 'pointer' : '';
      const key = f ? `${f.layer.id}|${f.properties._id || f.properties.cluster_id}` : null;
      if (key !== hovered) { hovered = key; }
      this.onHover(f ? this._hoverInfo(f) : null, e.originalEvent);
    });
    map.on('mouseout', () => this.onHover(null));
    map.on('click', async e => {
      const ids = this.interactive();
      const f = ids.length ? map.queryRenderedFeatures([[e.point.x - 4, e.point.y - 4], [e.point.x + 4, e.point.y + 4]], { layers: ids })[0] : null;
      if (!f) { this.onSelect(null, null, e.lngLat); return; }
      if (f.properties.cluster_id != null) {
        const src = map.getSource(f.source);
        const z = await src.getClusterExpansionZoom(f.properties.cluster_id);
        map.easeTo({ center: f.geometry.coordinates, zoom: Math.min(z + 0.3, 14), duration: 700 });
        return;
      }
      const slug = f.properties._slug;
      if (f.layer.id.endsWith('-line')) {
        const l = (this.data.get(slug)?.lines || []).find(x => String(x.id) === f.properties._id);
        this.onSelect(this.defs.get(slug), l ? { id: l.id, name: l.name, p: l.p || {}, lat: e.lngLat.lat, lon: e.lngLat.lng, _line: true } : null);
        return;
      }
      const it = this.items.get(slug)?.get(f.properties._id);
      if (it) { this.select({ slug, id: it.id, item: it }); this.onSelect(this.defs.get(slug), it); }
    });
  }

  _hoverInfo(f) {
    const p = f.properties;
    const d = this.defs.get(p._slug || f.layer.id.slice(P.length).replace(/-(pt|cl|line)$/, ''));
    if (p.cluster_id != null) return { title: `${p.point_count_abbreviated}`, sub: d?.name, cluster: true };
    return { title: p.name || '—', sub: d?.name, def: d };
  }

  // ---------- panel / arama ----------
  _counts() { this.onCounts(this.meta); }

  search(q, limit = 12) {
    const s = q.trim().toLocaleLowerCase();
    if (s.length < 2) return [];
    const out = [];
    for (const [slug, its] of this.items) {
      for (const it of its.values()) {
        const hay = `${it.name || ''} ${it.p?.reg || ''} ${it.p?.hex || ''} ${it.p?.country || ''}`.toLocaleLowerCase();
        if (hay.includes(s)) { out.push({ def: this.defs.get(slug), it }); if (out.length >= limit * 4) break; }
      }
    }
    out.sort((a, b) => ((b.it.name || '').toLocaleLowerCase().startsWith(s) ? 1 : 0) - ((a.it.name || '').toLocaleLowerCase().startsWith(s) ? 1 : 0));
    return out.slice(0, limit);
  }

  focus(def, it) {
    this.select({ slug: def.slug, id: it.id, item: it });
    this.map.flyTo({ center: [it._lon ?? it.lon, it._lat ?? it.lat], zoom: Math.max(this.map.getZoom(), def.kind === 'satellite' || def.kind === 'iss' ? 3 : 8), duration: 1800, essential: true });
    this.onSelect(def, it);
  }
}
