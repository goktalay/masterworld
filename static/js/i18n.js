// Dil: ?lang > kayıtlı ayar > navigator.languages > İngilizce. Sözlükler /i18n/<dil>.json; eksik anahtar İngilizceye düşer.
export const LANGS = ['tr', 'en', 'de', 'fr', 'es', 'ar', 'ru', 'zh'];
export const LANG_NAMES = { tr: 'Türkçe', en: 'English', de: 'Deutsch', fr: 'Français', es: 'Español', ar: 'العربية', ru: 'Русский', zh: '中文' };
let dict = {}, base = {}, lang = 'en';

export function pickLang(saved) {
  const q = new URLSearchParams(location.search).get('lang');
  if (q && LANGS.includes(q)) return q;
  if (saved && LANGS.includes(saved)) return saved;
  for (const l of navigator.languages || [navigator.language || 'en']) {
    const k = String(l).toLowerCase().split('-')[0];
    if (LANGS.includes(k)) return k;
  }
  return 'en';
}

async function load(l) {
  try { const r = await fetch(`/i18n/${l}.json`); if (r.ok) return await r.json(); } catch { /* çevrimdışı */ }
  return {};
}

export async function setLang(l) {
  lang = LANGS.includes(l) ? l : 'en';
  if (!Object.keys(base).length) base = await load('en');
  dict = lang === 'en' ? base : await load(lang);
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  apply(document);
  return lang;
}

export const getLang = () => lang;

export function t(key, vars) {
  let s = dict[key] ?? base[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, v);
  return s;
}

export function apply(root) {
  root.querySelectorAll('[data-i18n]').forEach(e => { e.textContent = t(e.dataset.i18n); });
  root.querySelectorAll('[data-i18n-ph]').forEach(e => { e.placeholder = t(e.dataset.i18nPh); });
  root.querySelectorAll('[data-i18n-title]').forEach(e => { e.title = t(e.dataset.i18nTitle); e.setAttribute('aria-label', e.title); });
}

const rtf = () => new Intl.RelativeTimeFormat(lang, { numeric: 'auto' });
export function ago(sec) {
  const d = sec - Date.now() / 1000;
  const a = Math.abs(d);
  if (a < 60) return rtf().format(Math.round(d), 'second');
  if (a < 3600) return rtf().format(Math.round(d / 60), 'minute');
  if (a < 86400) return rtf().format(Math.round(d / 3600), 'hour');
  return rtf().format(Math.round(d / 86400), 'day');
}
export const fmtNum = (v, d = 0) => (v == null ? '—' : Number(v).toLocaleString(lang, { maximumFractionDigits: d }));
export const fmtTime = sec => new Date(sec * 1000).toLocaleString(lang, { dateStyle: 'medium', timeStyle: 'short' });
