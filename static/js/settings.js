// Kullanıcı ayarları. Üye değilse yalnız localStorage ('mw.settings'); üyeyse ayrıca mastertool.download /api/mw/profile (Bearer).
// Girişte hesaptaki profil kazanır; yalnız oturum açıkken yapılıp henüz gönderilemeyen yerel değişiklik (pending) öne geçer. Uzak yazım 3 sn ertelenir; kişisel veri yok (katmanlar, altlık, görünüm, dil, ses).
const KEY = 'mw.settings';
const TOKEN = 'mw.token';
let state = { v: 1, layers: {}, base: 'dark', view: null, lang: null, volume: 0.8, panel: null, labels: true, updated_at: 0 };
let meta = null, timer = 0, listeners = [];

export function init(m) {
  meta = m;
  try { const s = JSON.parse(localStorage.getItem(KEY) || 'null'); if (s && s.v === 1) state = { ...state, ...s }; } catch { /* özel mod */ }
  return state;
}
export const get = () => state;
export const token = () => { try { return localStorage.getItem(TOKEN) || ''; } catch { return ''; } };
export function setToken(t) { try { if (t) localStorage.setItem(TOKEN, t); else localStorage.removeItem(TOKEN); } catch { /* özel mod */ } }
export const onSync = fn => listeners.push(fn);
const emit = s => listeners.forEach(fn => { try { fn(s); } catch { /* */ } });

const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* kota */ } };

export function set(patch) {
  state = { ...state, ...patch, updated_at: Date.now() };
  if (token()) { state.pending = true; clearTimeout(timer); timer = setTimeout(push, 3000); }
  save();
}

const acct = path => `${meta.mt_url.replace(/\/$/, '')}/api/${meta.mt_app}${path}`;

export async function mt(path, { method = 'GET', body } = {}) {
  const r = await fetch(acct(path), { method, credentials: 'omit',
    headers: { Authorization: `Bearer ${token()}`, 'x-sshm': '1', ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined });
  if (r.status === 401) { setToken(''); emit({ state: 'signed_out' }); throw new Error('unauthorized'); }
  if (!r.ok) throw new Error(`http_${r.status}`);
  return r.json();
}

async function push() {
  if (!token()) return;
  emit({ state: 'saving' });
  const { pending, ...profile } = state;
  try { await mt('/profile', { method: 'PUT', body: { profile } }); state.pending = false; save(); emit({ state: 'saved' }); }
  catch { emit({ state: 'error' }); }
}

/** Girişte / açılışta: hesapta profil varsa uygulanır (true döner) — bekleyen yerel değişiklik yoksa. Hesapta profil yoksa yerel olan yazılır. */
export async function pull() {
  if (!token()) return { user: null, applied: false };
  const d = await mt('/profile');
  const remote = d.profile;
  if (remote && remote.v === 1 && !state.pending) {
    state = { ...state, ...remote, pending: false };
    save();
    return { user: d.user, applied: true };
  }
  push();
  return { user: d.user, applied: false };
}

export function flush() { if (timer) { clearTimeout(timer); push(); } }
