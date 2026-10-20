// Uydu konumu (görsel amaçlı): CelesTrak OMM ortalama elemanlarından iki cisim Kepler + J2 seküler (RAAN / perigee kayması).
// SGP4 değildir; LEO'da birkaç gün içinde onlarca km mertebesinde sapar — küre üzerinde gösterim için yeterli.
const MU = 398600.4418, RE = 6378.137, J2 = 1.08262668e-3, TWO_PI = Math.PI * 2, D2R = Math.PI / 180;

export function elements(omm) {
  const n = Number(omm.MEAN_MOTION) * TWO_PI / 86400;              // rad/s
  if (!(n > 0)) return null;
  const e = Number(omm.ECCENTRICITY) || 0, i = Number(omm.INCLINATION) * D2R;
  const a = Math.cbrt(MU / (n * n));
  const p = a * (1 - e * e);
  const k = 1.5 * J2 * (RE / p) ** 2 * n;
  return { n, e, i, a, epoch: Date.parse(String(omm.EPOCH).endsWith('Z') ? omm.EPOCH : omm.EPOCH + 'Z'),
    raan0: Number(omm.RA_OF_ASC_NODE) * D2R, argp0: Number(omm.ARG_OF_PERICENTER) * D2R, M0: Number(omm.MEAN_ANOMALY) * D2R,
    draan: -k * Math.cos(i), dargp: k * (2 - 2.5 * Math.sin(i) ** 2) };
}

function gmst(ms) {
  const d = ms / 86400000 + 2440587.5 - 2451545.0;
  return ((280.46061837 + 360.98564736629 * d) % 360) * D2R;
}

/** el + zaman (ms) → {lat, lon, alt (km)} */
export function position(el, ms) {
  const dt = (ms - el.epoch) / 1000;
  let M = (el.M0 + el.n * dt) % TWO_PI;
  let E = el.e < 0.8 ? M : Math.PI;
  for (let k = 0; k < 12; k++) { const f = E - el.e * Math.sin(E) - M; E -= f / (1 - el.e * Math.cos(E)); if (Math.abs(f) < 1e-9) break; }
  const nu = 2 * Math.atan2(Math.sqrt(1 + el.e) * Math.sin(E / 2), Math.sqrt(1 - el.e) * Math.cos(E / 2));
  const r = el.a * (1 - el.e * Math.cos(E));
  const raan = el.raan0 + el.draan * dt, argp = el.argp0 + el.dargp * dt, u = argp + nu;
  const cO = Math.cos(raan), sO = Math.sin(raan), ci = Math.cos(el.i), si = Math.sin(el.i), cu = Math.cos(u), su = Math.sin(u);
  const x = r * (cO * cu - sO * su * ci), y = r * (sO * cu + cO * su * ci), z = r * (su * si);
  const th = gmst(ms);
  const xe = x * Math.cos(th) + y * Math.sin(th), ye = -x * Math.sin(th) + y * Math.cos(th);
  const lon = Math.atan2(ye, xe) / D2R;
  const lat = Math.atan2(z, Math.hypot(xe, ye)) / D2R;
  return { lat, lon: ((lon + 540) % 360) - 180, alt: r - RE };
}

/** Bir tam tur yer izi (antimeridyende bölünmüş çoklu çizgi) */
export function groundTrack(el, ms, steps = 180) {
  const period = TWO_PI / el.n * 1000;
  const lines = [[]];
  let prev = null;
  for (let s = 0; s <= steps; s++) {
    const p = position(el, ms + (s / steps) * period);
    if (prev && Math.abs(p.lon - prev.lon) > 180) lines.push([]);
    lines[lines.length - 1].push([p.lon, p.lat]);
    prev = p;
  }
  return lines.filter(l => l.length > 1);
}

export const periodMin = el => TWO_PI / el.n / 60;
