// Engraved orthographic globe of event sources, grouped by city.
// mountGlobe(container, { events, onSelectPlace }) → { update(events), highlight(placeId | null), destroy() }
import { geoOrthographic, geoPath, geoGraticule, geoDistance } from "https://cdn.jsdelivr.net/npm/d3-geo@3/+esm";
import { feature } from "https://cdn.jsdelivr.net/npm/topojson-client@3/+esm";

const LAND_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/land-110m.json";
const STYLE_ID = "gw-globe-style";
const SPEED = 4, PAUSE_MS = 3000, TWEEN_MS = 900, HALF = Math.PI / 2;
const SPHERE = { type: "Sphere" };
const GRATICULE = geoGraticule().step([30, 30])();

// city, ISO-2, lat, lon, ...sources headquartered / operating there
const CITIES = [
  ["Washington", "US", 38.8951, -77.0364, "BEA", "BLS", "SEC Press Releases", "Federal Reserve", "US Treasury"],
  ["New York", "US", 40.7069, -74.0113, "MSCI", "Nasdaq", "New York Stock Exchange", "DTCC", "ICE Futures U.S.", "S&P Global"],
  ["Chicago", "US", 41.8786, -87.6359, "CME Group", "CBOE"],
  ["Tempe", "US", 33.4255, -111.94, "ISM"],
  ["Ottawa", "CA", 45.4215, -75.6972, "Bank of Canada"],
  ["Toronto", "CA", 43.6481, -79.3816, "TSX"],
  ["Aguascalientes", "MX", 21.8853, -102.2916, "INEGI"],
  ["São Paulo", "BR", -23.5466, -46.6339, "B3 (Brasil)"],
  ["Rio de Janeiro", "BR", -22.9068, -43.1729, "IBGE"],
  ["London", "GB", 51.5142, -0.0885, "Bank of England", "London Stock Exchange"],
  ["Newport", "GB", 51.5686, -3.0003, "ONS UK Release Calendar"],
  ["Amsterdam", "NL", 52.3676, 4.9041, "Euronext"],
  ["Frankfurt", "DE", 50.1109, 8.6821, "Deutsche Börse", "Eurex", "ECB", "ECB Press Releases"],
  ["Munich", "DE", 48.1351, 11.582, "Ifo Institute"],
  ["Luxembourg", "LU", 49.6116, 6.1319, "Eurostat"],
  ["Zurich", "CH", 47.3769, 8.5417, "SIX Swiss Exchange"],
  ["Milan", "IT", 45.4642, 9.19, "Borsa Italiana"],
  ["Madrid", "ES", 40.4168, -3.7038, "BME"],
  ["Stockholm", "SE", 59.3293, 18.0686, "Nasdaq Nordic"],
  ["Riyadh", "SA", 24.7136, 46.6753, "Saudi Exchange"],
  ["Mumbai", "IN", 18.9294, 72.8331, "NSE India"],
  ["Singapore", "SG", 1.2797, 103.8501, "Singapore Exchange"],
  ["Hong Kong", "HK", 22.2819, 114.1582, "HKEX"],
  ["Shanghai", "CN", 31.2304, 121.4737, "Shanghai Stock Exchange"],
  ["Beijing", "CN", 39.9042, 116.4074, "PBoC", "China NBS"],
  ["Busan", "KR", 35.1796, 129.0756, "Korea Exchange"],
  ["Tokyo", "JP", 35.684, 139.7745, "Bank of Japan", "JPX / TSE", "Tokyo Stock Exchange"],
  ["Sydney", "AU", -33.8688, 151.2093, "ASX", "RBA"],
];
export const SOURCE_LOCATIONS = Object.fromEntries(CITIES.flatMap(([city, country, lat, lon, ...sources]) =>
  sources.map(s => [s, { city, country, lat, lon }])));

const TOKENS = {
  paper: ["--paper", "#F4F1EA"], paper2: ["--paper-2", "#EAE6DB"], ink: ["--ink", "#17160F"],
  ink2: ["--ink-2", "#4A463C"], ink3: ["--ink-3", "#6B6658"], rule: ["--rule", "#D5CFC0"],
  accent: ["--accent", "#8F6410"], ex: ["--ex", "#2E5A86"], ec: ["--ec", "#9C4F1A"],
};
const SANS = '"IBM Plex Sans", system-ui, sans-serif';
const CSS = `
.gw-globe{position:relative;width:100%;user-select:none;-webkit-user-select:none}
.gw-globe-canvas{display:block;width:100%;height:auto;aspect-ratio:1/1;touch-action:pan-y;cursor:grab;-webkit-tap-highlight-color:transparent}
.gw-globe-canvas.is-drag{cursor:grabbing}
.gw-globe-tip{position:absolute;left:0;top:0;z-index:2;max-width:min(240px,85%);padding:6px 8px;box-sizing:border-box;pointer-events:none;
  background:var(--paper,#F4F1EA);color:var(--ink,#17160F);border:1px solid var(--rule,#D5CFC0);border-radius:4px;font:12px/1.4 ${SANS}}
.gw-globe-tip[hidden]{display:none}
.gw-globe-tip b{font-weight:600}
.gw-globe-num,.gw-globe-cc{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:11px}
.gw-globe-cc{margin-left:6px;color:var(--ink-3,#6B6658)}
.gw-globe-next{margin-top:2px;color:var(--ink-2,#4A463C)}
.gw-globe-list{position:absolute;left:0;bottom:0;margin:0;padding:0;list-style:none}
.gw-globe-list button{position:absolute;width:1px;height:1px;margin:-1px;padding:0;border:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.gw-globe-list button:focus-visible{width:auto;height:auto;margin:0;left:0;bottom:4px;clip:auto;overflow:visible;padding:3px 8px;
  background:var(--paper,#F4F1EA);color:var(--ink,#17160F);border:1px solid var(--accent,#8F6410);border-radius:4px;font:12px/1.4 ${SANS};outline:none}
`;

const MON = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split(" ");
const pad = n => String(n).padStart(2, "0");
const isoToday = () => { const d = new Date(); return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) };
const fmtDate = s => { const [y, m, d] = s.split("-"); return d + " " + MON[m - 1] + (+y === new Date().getFullYear() ? "" : " " + y) };
const trunc = (s, n = 54) => s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s;
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const slug = s => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

let landP = null, mounts = 0;
const loadLand = () => landP ||= fetch(LAND_URL)
  .then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json() })
  .then(topo => feature(topo, topo.objects.land))
  .catch(err => { landP = null; console.warn("[globe] land outline unavailable, drawing sphere only:", err); return null });

export function mountGlobe(container, { events = [], onSelectPlace } = {}) {
  if (!mounts++ && !document.getElementById(STYLE_ID))
    document.head.append(Object.assign(document.createElement("style"), { id: STYLE_ID, textContent: CSS }));

  const wrap = document.createElement("div");
  wrap.className = "gw-globe";
  wrap.innerHTML = '<canvas class="gw-globe-canvas" role="img"></canvas><div class="gw-globe-tip" aria-hidden="true" hidden></div><ul class="gw-globe-list" aria-label="Places on the globe"></ul>';
  const [canvas, tip, list] = wrap.children;
  container.append(wrap);

  const c = canvas.getContext("2d");
  const proj = geoOrthographic().clipAngle(90), path = geoPath(proj, c);
  const mqDark = matchMedia("(prefers-color-scheme: dark)"), mqMotion = matchMedia("(prefers-reduced-motion: reduce)");
  let C, P = [], land = null, size = 0, dpr = 1, rot = [40, -35, 0];
  let sel = null, peek = null, tipId = null, hover = false, drag = null, tween = null;
  let raf = 0, last = 0, dirty = true, resumeAt = 0, resumeT = 0, onScreen = true, dead = false;

  const readColors = () => {
    const cs = getComputedStyle(container);
    C = Object.fromEntries(Object.entries(TOKENS).map(([k, [v, f]]) => [k, cs.getPropertyValue(v).trim() || f]));
  };

  const build = evts => {
    const today = isoToday(), byId = new Map();
    for (const e of evts || []) {
      const loc = SOURCE_LOCATIONS[e.source];
      if (!loc) continue;
      const id = slug(loc.city);
      let p = byId.get(id);
      if (!p) byId.set(id, p = { place: { id, label: loc.city, country: loc.country, lat: loc.lat, lon: loc.lon, sources: [] }, n: 0, next: null, ex: false, ec: false });
      if (!p.place.sources.includes(e.source)) p.place.sources.push(e.source);
      if (!(e.date >= today)) continue;
      p.n++;
      if (e.type === "exchange") p.ex = true;
      if (e.type === "economics") p.ec = true;
      if (!p.next || e.date < p.next.date) p.next = e;
    }
    P = [...byId.values()].sort((a, b) => b.n - a.n || a.place.label.localeCompare(b.place.label));
    const max = Math.max(1, ...P.map(p => p.n));
    for (const p of P) { p.r = p.n ? 3 + 6 * Math.sqrt(p.n / max) : 2.5; p.vis = false }
  };

  const renderList = () => {
    const active = list.contains(document.activeElement) ? document.activeElement.dataset.id : null;
    list.replaceChildren(...P.map(p => {
      const li = document.createElement("li"), b = document.createElement("button");
      b.type = "button";
      b.dataset.id = p.place.id;
      b.textContent = `${p.place.label} — ${p.n} upcoming`;
      b.setAttribute("aria-pressed", p.place.id === sel);
      li.append(b);
      return li;
    }));
    const again = active && list.querySelector(`[data-id="${active}"]`);
    if (again) again.focus(); else if (active) peek = null;
    canvas.setAttribute("aria-label", `Globe showing ${P.length} places, ${P.filter(p => p.n).length} with upcoming dates`);
  };

  const spinning = now => !mqMotion.matches && !sel && !peek && !hover && !drag && now >= resumeAt;
  const kick = () => { if (!raf && onScreen && !document.hidden && !dead) raf = requestAnimationFrame(tick) };
  const invalidate = () => { dirty = true; kick() };
  const pause = () => { resumeAt = performance.now() + PAUSE_MS; clearTimeout(resumeT); resumeT = setTimeout(kick, PAUSE_MS) };

  function tick(now) {
    raf = 0;
    const dt = last ? Math.min(64, now - last) : 0;
    last = now;
    if (tween) {
      const k = Math.min(1, (now - tween.t0) / TWEEN_MS), e = k < .5 ? 4 * k ** 3 : 1 - (2 - 2 * k) ** 3 / 2;
      rot = tween.from.map((v, i) => v + (tween.to[i] - v) * e);
      if (k === 1) tween = null;
      dirty = true;
    } else if (spinning(now)) {
      rot[0] = (rot[0] + SPEED * dt / 1000) % 360;
      dirty = true;
    }
    if (dirty) draw();
    if ((tween || spinning(now)) && onScreen && !document.hidden) raf = requestAnimationFrame(tick); else last = 0;
  }

  const aim = id => {
    const p = P.find(q => q.place.id === id);
    if (!p) return;
    const to = [-p.place.lon, clamp(-p.place.lat, -60, 60), 0];
    if (mqMotion.matches) { rot = to; tween = null; return invalidate() }
    const from = rot.slice();
    from[0] = to[0] + ((from[0] - to[0]) % 360 + 540) % 360 - 180;
    tween = { from, to, t0: performance.now() };
    kick();
  };

  const circle = (x, y, r) => { c.beginPath(); c.arc(x, y, r, 0, 2 * Math.PI) };
  const shape = (obj, fill, stroke, width = 1, alpha = 1) => {
    c.beginPath(); path(obj);
    if (fill) { c.fillStyle = fill; c.fill() }
    if (stroke) { c.globalAlpha = alpha; c.strokeStyle = stroke; c.lineWidth = width; c.stroke(); c.globalAlpha = 1 }
  };

  const marker = p => {
    const { x, y, r } = p;
    if (!p.n) { c.globalAlpha *= .55; circle(x, y, r); c.strokeStyle = C.ink3; c.lineWidth = 1; c.stroke(); return }
    if (p.ec) { circle(x, y, r - .75); c.fillStyle = C.paper2; c.fill(); c.strokeStyle = C.ec; c.lineWidth = 1.5; c.stroke() }
    if (p.ex) { circle(x, y, p.ec ? r * .5 : r); c.fillStyle = C.ex; c.fill(); if (!p.ec) { c.strokeStyle = C.paper2; c.lineWidth = .75; c.stroke() } }
  };

  const labels = mark => {
    const boxes = [];
    c.textBaseline = "middle"; c.lineJoin = "round";
    const put = (p, text, strong) => {
      c.font = (strong ? "600 11px " : "500 10.5px ") + SANS;
      const w = c.measureText(text).width, gap = p.r + (strong ? 8 : 4);
      let x = p.x + gap;
      if (x + w > size - 2) x = p.x - gap - w;
      const b = [x - 2, p.y - 7, x + w + 2, p.y + 7];
      if (boxes.some(o => b[0] < o[2] && b[2] > o[0] && b[1] < o[3] && b[3] > o[1])) return;
      boxes.push(b);
      c.globalAlpha = p.a;
      c.strokeStyle = C.paper2; c.lineWidth = 3; c.strokeText(text, x, p.y);
      c.fillStyle = strong ? C.ink : C.ink2; c.fillText(text, x, p.y);
      c.globalAlpha = 1;
    };
    const hp = P.find(p => p.vis && p.place.id === mark);
    if (hp) put(hp, hp.place.label + " · " + hp.n, true);
    if (size >= 300) P.slice(0, 3).filter(p => p.vis && p.n && p !== hp).forEach(p => put(p, p.place.label));
  };

  function draw() {
    dirty = false;
    if (!size) return;
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, size, size);
    proj.rotate(rot);
    shape(SPHERE, C.paper2);
    if (land) shape(land, C.rule, C.ink3, .5, .5);
    shape(GRATICULE, null, C.ink3, .5, .22);
    shape(SPHERE, null, C.ink3, 1);
    const center = [-rot[0], -rot[1]], mark = peek || sel;
    for (const p of P) {
      const d = geoDistance(center, [p.place.lon, p.place.lat]);
      p.vis = d < HALF - .02;
      if (!p.vis) continue;
      [p.x, p.y] = proj([p.place.lon, p.place.lat]);
      p.a = Math.min(1, (HALF - d) / .2);
      c.globalAlpha = p.a;
      marker(p);
    }
    const hp = P.find(p => p.vis && p.place.id === mark);
    if (hp) { c.globalAlpha = hp.a; circle(hp.x, hp.y, hp.r + 4); c.strokeStyle = C.accent; c.lineWidth = 1.5; c.stroke() }
    c.globalAlpha = 1;
    labels(mark);
    if (tipId) placeTip();
  }

  const showTip = p => {
    tipId = p ? p.place.id : null;
    if (!p) { tip.hidden = true; return }
    const nx = p.next;
    tip.innerHTML = `<b>${esc(p.place.label)}</b><span class="gw-globe-cc">${esc(p.place.country)}</span>`
      + `<div><span class="gw-globe-num">${p.n}</span> upcoming</div>`
      + `<div class="gw-globe-next">${nx ? `<span class="gw-globe-num">${fmtDate(nx.date)}</span> ${esc(trunc(nx.title || ""))}` : "No upcoming dates"}</div>`;
    tip.hidden = false;
    placeTip();
  };
  function placeTip() {
    const p = P.find(q => q.place.id === tipId);
    if (!p || !p.vis) { tipId = null; tip.hidden = true; return }
    const k = canvas.clientWidth / size, w = tip.offsetWidth, h = tip.offsetHeight, W = wrap.clientWidth, H = wrap.clientHeight;
    const px = p.x * k, py = p.y * k, g = (p.r + 8) * k;
    let x = px + g, y = py - h / 2;
    if (x + w > W) x = px - g - w;
    if (x < 0) { x = clamp(px - w / 2, 0, W - w); y = py + g + h > H ? py - g - h : py + g }
    tip.style.transform = `translate(${Math.round(x)}px,${Math.round(clamp(y, 0, H - h))}px)`;
  }

  const choose = p => {
    if (!p) return;
    const next = p.place.id === sel ? null : p.place;
    api.highlight(next && next.id);
    onSelectPlace?.(next);
  };
  const at = e => { const b = canvas.getBoundingClientRect(); return [(e.clientX - b.left) * size / b.width, (e.clientY - b.top) * size / b.height] };
  const hit = ([x, y]) => {
    let best = null, bd = Infinity;
    for (const p of P) {
      if (!p.vis) continue;
      const d = Math.hypot(p.x - x, p.y - y);
      if (d < Math.max(p.r + 4, 10) && d < bd) { best = p; bd = d }
    }
    return best;
  };
  const endDrag = () => { drag = null; canvas.classList.remove("is-drag"); pause() };

  const on = {
    pointerdown: e => {
      if (e.button) return;
      drag = { x: e.clientX, y: e.clientY, rot: rot.slice(), moved: false };
      tween = null;
      canvas.setPointerCapture(e.pointerId);
    },
    pointermove: e => {
      if (drag) {
        const dx = e.clientX - drag.x, dy = e.clientY - drag.y, k = 180 / Math.PI / proj.scale();
        if (!drag.moved && Math.hypot(dx, dy) < 4) return;
        if (!drag.moved) { drag.moved = true; canvas.classList.add("is-drag"); canvas.style.cursor = ""; showTip(null) }
        rot = [drag.rot[0] + dx * k, clamp(drag.rot[1] - dy * k, -80, 80), 0];
        return invalidate();
      }
      const p = hit(at(e));
      canvas.style.cursor = p ? "pointer" : "";
      if ((p ? p.place.id : null) !== tipId) showTip(p);
    },
    pointerup: e => {
      if (!drag) return;
      const tap = !drag.moved;
      endDrag();
      if (!tap) return;
      const p = hit(at(e));
      if (p) { showTip(p); choose(p) } else if (e.pointerType === "touch") showTip(null);
    },
    pointercancel: () => { if (drag) endDrag() },
    pointerenter: () => { hover = true },
    pointerleave: e => { hover = false; pause(); if (e.pointerType !== "touch") showTip(null) },
  };
  for (const k in on) canvas.addEventListener(k, on[k]);

  const listOn = {
    click: e => { const id = e.target.dataset.id; if (id) choose(P.find(p => p.place.id === id)) },
    focusin: e => { const id = e.target.dataset.id; if (id) { peek = id; pause(); aim(id); invalidate() } },
    focusout: () => { peek = null; pause(); if (sel) aim(sel); invalidate() },
  };
  for (const k in listOn) list.addEventListener(k, listOn[k]);

  const onTheme = () => { readColors(); invalidate() };
  const onVisibility = () => kick();
  mqDark.addEventListener("change", onTheme);
  mqMotion.addEventListener("change", kick);
  document.addEventListener("visibilitychange", onVisibility);
  document.fonts?.addEventListener("loadingdone", invalidate);
  const mo = new MutationObserver(onTheme);
  mo.observe(document.documentElement, { attributes: true, attributeFilter: ["class", "data-theme"] });
  const io = new IntersectionObserver(([en]) => { onScreen = en.isIntersecting; kick() });
  io.observe(wrap);
  const ro = new ResizeObserver(([en]) => {
    const w = Math.floor(en.contentRect.width), r = devicePixelRatio || 1;
    if (!w || (w === size && r === dpr)) return;
    size = w; dpr = r;
    canvas.width = canvas.height = Math.round(w * r);
    proj.scale(w / 2 - 2).translate([w / 2, w / 2]);
    draw();
  });
  ro.observe(container);

  const api = {
    update(evts) {
      if (dead) return;
      readColors();
      build(evts);
      renderList();
      if (tipId) showTip(P.find(p => p.place.id === tipId) || null);
      invalidate();
    },
    highlight(id) {
      if (dead) return;
      sel = id || null;
      for (const b of list.querySelectorAll("button")) b.setAttribute("aria-pressed", b.dataset.id === sel);
      if (sel) aim(sel);
      invalidate();
    },
    destroy() {
      if (dead) return;
      dead = true;
      cancelAnimationFrame(raf); raf = 0;
      clearTimeout(resumeT);
      io.disconnect(); ro.disconnect(); mo.disconnect();
      mqDark.removeEventListener("change", onTheme);
      mqMotion.removeEventListener("change", kick);
      document.removeEventListener("visibilitychange", onVisibility);
      document.fonts?.removeEventListener("loadingdone", invalidate);
      for (const k in on) canvas.removeEventListener(k, on[k]);
      for (const k in listOn) list.removeEventListener(k, listOn[k]);
      wrap.remove();
      if (!--mounts) document.getElementById(STYLE_ID)?.remove();
    },
  };

  readColors();
  build(events);
  renderList();
  loadLand().then(l => { if (l && !dead) { land = l; invalidate() } });
  return api;
}
