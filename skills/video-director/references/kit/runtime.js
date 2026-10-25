// Runtime for seek(t) video pages. Every frame is a pure function of the global time T,
// so frames can be rendered in any order, in parallel, and re-rendered per shot.
//
// A project page calls mount(); each shot lives in shots/<id>.js and exports
//   render(ctx)          required; draws the shot at ctx.t (seconds since the shot started)
//   setup(ctx)           optional; builds DOM or canvases once, before any frame
// ctx: { id, T, t, p, dur, frame, params, style, meta, W, H, el, cue, ease, rng, rngAt }

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, u) => a + (b - a) * u;
// Progress of t through [a, b], clamped to 0..1.
export const range = (t, a, b) => (b === a ? (t >= b ? 1 : 0) : clamp((t - a) / (b - a)));
// Quantize time to a frame rate, for stepped styles (on twos, cut paper, sprites).
export const stepTime = (t, fps) => (fps > 0 ? Math.floor(t * fps + 1e-6) / fps : t);

function hashString(s) {
  let h = 2166136261;
  for (const ch of s) {
    h ^= ch.codePointAt(0);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

// Seeded PRNG (mulberry32). Same seed, same sequence, every frame.
export function rng(seed) {
  let a = typeof seed === 'number' ? seed >>> 0 : hashString(String(seed));
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// CSS-style cubic-bezier easing: returns u => eased u.
export function bezier(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const sx = s => ((ax * s + bx) * s + cx) * s;
  const sy = s => ((ay * s + by) * s + cy) * s;
  const dx = s => (3 * ax * s + 2 * bx) * s + cx;
  return u => {
    if (u <= 0) return 0;
    if (u >= 1) return 1;
    let s = u;
    for (let i = 0; i < 8; i++) {
      const err = sx(s) - u;
      if (Math.abs(err) < 1e-6) return sy(s);
      const d = dx(s);
      if (Math.abs(d) < 1e-6) break;
      s -= err / d;
    }
    let lo = 0, hi = 1;
    s = u;
    for (let i = 0; i < 30; i++) {
      if (sx(s) < u) lo = s; else hi = s;
      s = (lo + hi) / 2;
    }
    return sy(s);
  };
}

export const ease = {
  linear: u => u,
  outCubic: u => 1 - (1 - u) ** 3,
  inOutCubic: u => (u < 0.5 ? 4 * u * u * u : 1 - (-2 * u + 2) ** 3 / 2),
  outExpo: u => (u >= 1 ? 1 : 1 - 2 ** (-10 * u)),
  outBack: (u, s = 1.70158) => 1 + (s + 1) * (u - 1) ** 3 + s * (u - 1) ** 2,
  snap: bezier(0.7, 0, 0.2, 1),
};

async function getJSON(url, fallback) {
  const res = await fetch(url);
  if (!res.ok) {
    if (fallback !== undefined) return fallback;
    throw new Error(`${url}: HTTP ${res.status}`);
  }
  return res.json();
}

export async function mount({ stageId = 'stage' } = {}) {
  try {
    const base = document.baseURI;
    const tl = await getJSON(new URL('timeline.json', base));
    const style = await getJSON(new URL('style.json', base), {});
    const meta = tl.meta;
    const W = meta.width, H = meta.height;

    const root = document.documentElement;
    for (const [k, v] of Object.entries(style.palette || {})) root.style.setProperty(`--${k}`, v);
    document.body.style.margin = '0';
    document.body.style.background = meta.background || style.palette?.bg || '#000';

    const stage = document.getElementById(stageId) || document.body.appendChild(document.createElement('div'));
    stage.id = stageId;
    Object.assign(stage.style, { position: 'relative', width: `${W}px`, height: `${H}px`, overflow: 'hidden' });

    const cueTimes = new Map((tl.cues || []).map(c => [c.id, c.t]));
    const used = new Set();
    window.__cuesUsed = used;
    const cue = id => {
      if (!cueTimes.has(id)) throw new Error(`unknown cue "${id}"`);
      used.add(id);
      return cueTimes.get(id);
    };
    // Resolve "cue:<id>" strings in params lazily, so reading one records the dependency.
    const resolveParams = params =>
      new Proxy(params || {}, {
        get(obj, key) {
          const v = obj[key];
          return typeof v === 'string' && v.startsWith('cue:') ? cue(v.slice(4)) : v;
        },
      });
    const easeOf = name => {
      const e = style.ease?.[name];
      if (Array.isArray(e)) return bezier(...e);
      if (ease[name]) return ease[name];
      throw new Error(`unknown ease "${name}"`);
    };

    const shots = [];
    for (const s of tl.shots) {
      const mod = await import(new URL(`shots/${s.id}.js`, base).href);
      // The runtime shows and hides the layer; the shot owns el's styles (display: grid etc.).
      const layer = document.createElement('div');
      Object.assign(layer.style, { position: 'absolute', inset: '0', display: 'none' });
      const el = document.createElement('div');
      el.className = 'shot';
      el.dataset.shot = s.id;
      Object.assign(el.style, { position: 'absolute', inset: '0' });
      layer.appendChild(el);
      stage.appendChild(layer);
      const ctx = {
        id: s.id, dur: s.end - s.start, params: resolveParams(s.params), style, meta, W, H, el,
        cue, ease: easeOf,
      };
      if (mod.setup) await mod.setup({ ...ctx, T: s.start, t: 0, p: 0, frame: 0, rng: rng(`${meta.seed}:${s.id}`) });
      shots.push({ s, mod, ctx, layer });
    }
    // Cues read during setup affect every frame; render.mjs adds them to each segment's dependencies.
    window.__setupCues = [...used];

    // Load every declared font and report the ones that failed, so render.mjs can refuse.
    await Promise.allSettled([...document.fonts].map(f => f.load()));
    await document.fonts.ready;
    const loaded = new Set([...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/["']/g, '')));
    window.__missingFonts = (style.fonts || []).filter(f => !loaded.has(f));

    const stepFps = style.step_fps || 0;
    window.DURATION = meta.duration;
    window.FPS = meta.fps;
    window.WIDTH = W;
    window.HEIGHT = H;
    window.seek = async T => {
      const frame = Math.round(T * meta.fps);
      for (const { s, mod, ctx, layer } of shots) {
        const on = T >= s.start && T < s.end;
        layer.style.display = on ? '' : 'none';
        if (!on) continue;
        const t = stepTime(T - s.start, stepFps);
        await mod.render({
          ...ctx, T, t, p: ctx.dur > 0 ? t / ctx.dur : 1, frame,
          rng: rng(`${meta.seed}:${s.id}`),
          rngAt: key => rng(`${meta.seed}:${s.id}:${key}`),
        });
      }
    };
    window.__ready = true;
  } catch (err) {
    window.__error = String(err && err.stack ? err.stack : err);
    throw err;
  }
}
