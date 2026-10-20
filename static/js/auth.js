// İsteğe bağlı üyelik — mastertool.download hesap servisi (uygulama kodu mw). SIMUMAV auth.js akışı:
//   prelogin {email} → {kdf} → auth_hash = b64(PBKDF2(PBKDF2(şifre, salt, iter), şifre, 1)) (şifre sunucuya gitmez)
//   login {email, auth_hash, device, app_version} → {token, user} — Bearer belirteci tarayıcıda (credentials:'omit'; CORS yalnız /api/mw/*)
import * as S from './settings.js';

const APP_VERSION = 'web-1';
const utf8 = s => new TextEncoder().encode(s);
const b64enc = bytes => btoa(String.fromCharCode(...bytes));
function b64dec(s) { const bin = atob(s.replace(/-/g, '+').replace(/_/g, '/')); const o = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) o[i] = bin.charCodeAt(i); return o; }
async function pbkdf2(keyBytes, saltBytes, iterations, len = 32) {
  const key = await crypto.subtle.importKey('raw', keyBytes, 'PBKDF2', false, ['deriveBits']);
  return new Uint8Array(await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt: saltBytes, iterations }, key, len * 8));
}
export async function computeAuthHash(password, kdf) {
  const master = await pbkdf2(utf8(password), b64dec(kdf.salt), kdf.iter, 32);
  return b64enc(await pbkdf2(master, utf8(password), 1, 32));
}
function deviceName() {
  const ua = navigator.userAgent || '';
  const os = /Android/i.test(ua) ? 'Android' : /iPhone|iPad/i.test(ua) ? 'iOS' : /Windows/i.test(ua) ? 'Windows' : /Mac/i.test(ua) ? 'macOS' : /Linux/i.test(ua) ? 'Linux' : 'Web';
  return `MASTERWORLD Web (${os})`;
}
class ApiError extends Error { constructor(code, status, retry) { super(code); this.code = code; this.status = status; this.retry = retry; } }

export function initAuth({ meta, t, onLogin, onLogout, onEvent = () => {} }) {
  const root = document.getElementById('auth');
  const msg = root.querySelector('#auth-msg'), title = root.querySelector('#auth-title');
  const views = [...root.querySelectorAll('[data-view]')];
  const forms = { login: root.querySelector('#f-login'), register: root.querySelector('#f-register'), forgot: root.querySelector('#f-forgot') };
  let lastFocus = null, waitTimer = 0, lastEmail = '', user = null;
  const url = path => `${meta.mt_url.replace(/\/$/, '')}/api/${meta.mt_app}${path}`;

  async function call(path, body, headers = {}) {
    let res;
    try {
      res = await fetch(url(path), { method: 'POST', headers: { 'Content-Type': 'application/json', 'x-sshm': '1', ...headers }, body: JSON.stringify(body), credentials: 'omit' });
    } catch { throw new ApiError('network', 0); }
    let data = null; try { data = await res.json(); } catch { /* gövdesiz */ }
    if (!res.ok) {
      const code = data?.code || (res.status === 429 ? 'rate_limited' : res.status === 401 ? 'bad_credentials' : 'generic');
      const retry = res.status === 429 ? Math.max(5, parseInt(res.headers.get('Retry-After') || '60', 10) || 60) : 0;
      throw new ApiError(code, res.status, retry);
    }
    return data || {};
  }
  const say = (kind, text) => { msg.hidden = !text; msg.className = 'msg ' + kind; msg.textContent = text || ''; };
  const busy = (form, on) => form.querySelectorAll('button, input').forEach(el => { el.disabled = on; });
  const errText = e => { const k = 'err.' + (e?.code || 'generic'); return t(k) !== k ? t(k) : t('err.generic'); };
  function wait(form, secs) {
    clearInterval(waitTimer);
    let s = secs;
    const tick = () => { say('wait', t('auth.wait', { s })); if (s-- <= 0) { clearInterval(waitTimer); waitTimer = 0; busy(form, false); say('', ''); } };
    busy(form, true); tick(); waitTimer = setInterval(tick, 1000);
  }
  function show(view) {
    views.forEach(v => { v.hidden = v.dataset.view !== view; });
    title.textContent = view === 'account' ? (user?.name || t('account.title')) : t(view === 'verify' ? 'auth.verify.title' : `auth.${view}.title`);
    if (view === 'account') root.querySelector('#acct-who').textContent = t('account.who', { name: user?.name || '', email: user?.email || '' });
    say('', '');
    root.hidden = false;
    if (view !== 'verify' && view !== 'account') root.querySelector(`[data-view="${view}"] input`)?.focus();
  }
  const close = () => { root.hidden = true; clearInterval(waitTimer); lastFocus?.focus?.(); };

  document.addEventListener('click', e => {
    const a = e.target.closest('[data-auth]');
    if (a) { e.preventDefault(); if (root.hidden) lastFocus = a; show(a.dataset.auth); return; }
    if (e.target.closest('[data-auth-close]') || e.target === root) close();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !root.hidden) close(); });

  forms.login.addEventListener('submit', async e => {
    e.preventDefault(); const f = e.target; const email = f.email.value.trim().toLowerCase(), password = f.password.value;
    busy(f, true); say('', '');
    try {
      const pre = await call('/auth/prelogin', { email });
      if (!pre?.kdf?.salt) throw new ApiError('generic', 500);
      const auth_hash = await computeAuthHash(password, pre.kdf);
      const data = await call('/auth/login', { email, auth_hash, device: deviceName(), app_version: APP_VERSION });
      if (!data?.token) throw new ApiError('generic', 500);
      S.setToken(data.token);
      user = data.user || { email };
      f.reset(); close();
      try { onEvent('login', { method: 'mastertool' }); } catch { /* */ }
      await onLogin(user);
    } catch (err) {
      if (err.retry) return wait(f, err.retry);
      if (err.code === 'unverified') { lastEmail = email; return verifyView(email); }
      say('err', errText(err));
    } finally { if (!waitTimer) busy(f, false); }
  });
  function verifyView(email) { show('verify'); root.querySelector('#verify-text').textContent = t('auth.verify.text', { email }); }

  forms.register.addEventListener('submit', async e => {
    e.preventDefault(); const f = e.target;
    const email = f.email.value.trim().toLowerCase(), name = f.name.value.trim(), password = f.password.value;
    say('', '');
    if (password.length < 8) return say('err', t('auth.pwshort'));
    if (password !== f.password2.value) return say('err', t('auth.pwmismatch'));
    busy(f, true);
    try {
      const pre = await call('/auth/prelogin', { email });
      const auth_hash = await computeAuthHash(password, pre.kdf);
      await call('/auth/register', { email, name, auth_hash, brand: meta.mt_app });
      lastEmail = email; verifyView(email);
      try { onEvent('sign_up', { method: 'mastertool' }); } catch { /* */ }
    } catch (err) { if (err.retry) return wait(f, err.retry); say('err', errText(err)); }
    finally { if (!waitTimer) busy(f, false); }
  });

  forms.forgot.addEventListener('submit', async e => {
    e.preventDefault(); const f = e.target;
    busy(f, true); say('', '');
    try { await call('/auth/forgot', { email: f.email.value.trim().toLowerCase(), brand: meta.mt_app }); say('ok', t('auth.forgot.sent')); }
    catch (err) { if (err.retry) return wait(f, err.retry); say('err', errText(err)); }
    finally { if (!waitTimer) busy(f, false); }
  });

  root.querySelector('#resend').addEventListener('click', async e => {
    e.preventDefault();
    try { await call('/auth/resend-verify', { email: lastEmail, brand: meta.mt_app }); say('ok', t('auth.verify.sent')); }
    catch (err) { say('err', errText(err)); }
  });

  root.querySelector('#btn-logout').addEventListener('click', async () => {
    S.flush();
    const tok = S.token();
    S.setToken(''); user = null; close();
    if (tok) try { await call('/auth/logout', {}, { Authorization: `Bearer ${tok}` }); } catch { /* belirteç zaten düşmüş olabilir */ }
    onLogout();
  });

  return {
    open: () => show(user ? 'account' : 'login'),
    setUser: u => { user = u; },
    user: () => user,
  };
}
