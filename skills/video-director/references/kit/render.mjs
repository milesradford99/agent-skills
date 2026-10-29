#!/usr/bin/env node
// Render a seek(t) project to video with headless Chromium and ffmpeg.
// Each shot's segment is cached by the hash of its inputs, so a revision re-renders only what changed.
//
//   node lib/render.mjs --project <slug>                       full render (cached per shot) + audio mux
//   node lib/render.mjs --project <slug> --scale 0.5 --step 2  fast preview
//   node lib/render.mjs --project <slug> --at 0.4,6.5,9.5      stills to renders/stills/
//   node lib/render.mjs --project <slug> --from 6 --to 7.5     one moment, no cache
//   node lib/render.mjs --project <slug> --check               determinism check only
//
// Run from video/ (the folder holding lib/, node_modules/ and the projects).
//
// Works with any page that meets the contract, whether or not it uses lib/runtime.js:
//   window.seek(t) draws the frame for time t (may be async), deterministically;
//   window.DURATION is set; window.__ready = true once fonts and assets are loaded (or window.__error on failure).
// Optional: window.__missingFonts (refuse to render), window.__cuesUsed / __setupCues (finer cache keys).

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createServer } from 'node:http';
import { once } from 'node:events';
import fs from 'node:fs';
import path from 'node:path';
import { parseArgs } from 'node:util';
import os from 'node:os';

const { values: o } = parseArgs({
  options: {
    project: { type: 'string' },
    from: { type: 'string' },
    to: { type: 'string' },
    at: { type: 'string' },
    scale: { type: 'string', default: '1' },
    step: { type: 'string', default: '1' },
    workers: { type: 'string', default: String(Math.max(1, Math.floor(os.cpus().length / 2))) },
    png: { type: 'boolean', default: false },   // lossless PNG capture; default is JPEG q95, ~5x faster on textured pages
    crf: { type: 'string' },
    out: { type: 'string' },
    check: { type: 'boolean', default: false },
    'chrome-arg': { type: 'string', multiple: true },
  },
});
if (!o.project) die('usage: node lib/render.mjs --project <slug> [--scale 0.5] [--step 2] [--at t,t] [--from s --to s] [--check]');

const projectDir = path.resolve(o.project);
const rootDir = path.dirname(projectDir);
const libDir = path.join(rootDir, 'lib');
const slug = path.basename(projectDir);
const scale = Number(o.scale);
const step = Math.max(1, parseInt(o.step, 10));
const preview = scale !== 1 || step !== 1;
const crf = o.crf ?? (preview ? '28' : '18');
const preset = preview ? 'veryfast' : 'medium';
const tl = readJSON(path.join(projectDir, 'timeline.json'));
const { fps, duration } = tl.meta;
const outFps = fps / step;
const renders = path.join(projectDir, 'renders');
const cacheDir = path.join(renders, 'cache');
fs.mkdirSync(cacheDir, { recursive: true });

function die(msg) {
  console.error(msg);
  process.exit(1);
}
function readJSON(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}
const sha = (...parts) => {
  const h = createHash('sha256');
  for (const p of parts) h.update(typeof p === 'string' || Buffer.isBuffer(p) ? p : JSON.stringify(p));
  return h.digest('hex').slice(0, 16);
};
function hashTree(dir, skip = new Set(), only = null) {
  if (!fs.existsSync(dir)) return '';
  const h = createHash('sha256');
  const walk = d => {
    for (const name of fs.readdirSync(d).sort()) {
      if (d === dir && skip.has(name)) continue;
      const p = path.join(d, name);
      if (fs.statSync(p).isDirectory()) walk(p);
      else if (only && !only.test(name)) continue;
      else h.update(path.relative(dir, p)).update(fs.readFileSync(p));
    }
  };
  walk(dir);
  return h.digest('hex');
}
const readOr = p => (fs.existsSync(p) ? fs.readFileSync(p) : '');

// ---- static server: serves video/ so pages can import ../lib/runtime.js ----
const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
  '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.otf': 'font/otf',
  '.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.mp4': 'video/mp4', '.glsl': 'text/plain',
};
const server = createServer((req, res) => {
  const rel = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const file = path.join(rootDir, path.normalize(rel));
  if (!file.startsWith(rootDir + path.sep) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404).end();
    return;
  }
  res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});
server.listen(0, '127.0.0.1');
await once(server, 'listening');
const pageUrl = `http://127.0.0.1:${server.address().port}/${slug}/index.html`;

const chromeArgs = o['chrome-arg'] ?? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'];
const browser = await chromium.launch({ args: chromeArgs });

async function openPage() {
  const page = await browser.newPage({
    viewport: { width: tl.meta.width, height: tl.meta.height },
    deviceScaleFactor: scale,
  });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => m.type() === 'error' && errors.push(m.text()));
  await page.goto(pageUrl);
  await page.waitForFunction(() => window.__ready === true || window.__error, null, { timeout: 120000 });
  const state = await page.evaluate(() => ({ error: window.__error, missing: window.__missingFonts || [] }));
  if (state.error) throw new Error(`page failed to mount:\n${state.error}`);
  if (state.missing.length) throw new Error(`fonts did not load: ${state.missing.join(', ')} (declare them with @font-face from assets/fonts/)`);
  page.__errors = errors;
  return page;
}
async function frameAt(page, T, video = false) {
  await page.evaluate(t => window.seek(t), T);
  if (video && !o.png) return page.screenshot({ type: 'jpeg', quality: 95, animations: 'disabled', caret: 'hide' });
  return page.screenshot({ type: 'png', animations: 'disabled', caret: 'hide' });
}
function encoder(file, rate) {
  // JPEG frames are full-range; convert to TV range so colours match the PNG path.
  const args = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(rate), '-c:v', o.png ? 'png' : 'mjpeg', '-i', '-',
    ...(o.png ? [] : ['-vf', 'scale=in_range=full:out_range=tv,format=yuv420p']),
    '-c:v', 'libx264', '-preset', preset, '-crf', crf, '-pix_fmt', 'yuv420p',
    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-r', String(rate), file];
  const proc = spawn('ffmpeg', args, { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((resolve, reject) =>
    proc.on('close', code => (code === 0 ? resolve() : reject(new Error(`ffmpeg exited ${code} for ${file}`)))));
  return {
    async write(buf) {
      if (!proc.stdin.write(buf)) await once(proc.stdin, 'drain');
    },
    async end() {
      proc.stdin.end();
      await done;
    },
  };
}
function ffmpeg(args) {
  return new Promise((resolve, reject) => {
    const p = spawn('ffmpeg', ['-y', '-loglevel', 'error', ...args], { stdio: 'inherit' });
    p.on('close', code => (code === 0 ? resolve() : reject(new Error(`ffmpeg ${args.join(' ')} exited ${code}`))));
  });
}
// Frames i*step for i in [first, last), where frame n shows time n/fps.
function framesIn(start, end) {
  const first = Math.ceil((start * fps) / step - 1e-9);
  const last = Math.ceil((Math.min(end, duration) * fps) / step - 1e-9);
  const list = [];
  for (let i = first; i < last; i++) list.push((i * step) / fps);
  return list;
}

async function run() {
  // ---- stills ----
  if (o.at) {
    const page = await openPage();
    const dir = path.join(renders, 'stills');
    fs.mkdirSync(dir, { recursive: true });
    for (const t of o.at.split(',').map(Number)) {
      const file = path.join(dir, `t${t.toFixed(2).padStart(6, '0')}.png`);
      fs.writeFileSync(file, await frameAt(page, t));
      console.log(file);
    }
    return;
  }

  // ---- determinism ----
  if (o.check) {
    const page = await openPage();
    const times = [0.37, 0.11, 0.83].map(u => Math.round(u * duration * fps) / fps);
    const a = await frameAt(page, times[0]);
    await frameAt(page, times[1]);
    await frameAt(page, times[2]);
    const b = await frameAt(page, times[0]);
    const c = await frameAt(page, times[0]);
    const ok = a.equals(b) && b.equals(c);
    console.log(ok ? `deterministic: frame at ${times[0]}s identical after seeking away and back`
      : `NOT deterministic: frame at ${times[0]}s changed after seeking elsewhere. Look for Date.now, timers, rAF loops, CSS transitions or unseeded Math.random.`);
    if (page.__errors.length) console.log(`page errors:\n${page.__errors.join('\n')}`);
    process.exitCode = ok ? 0 : 1;
    return;
  }

  // ---- one moment, uncached ----
  if (o.from !== undefined || o.to !== undefined) {
    const from = Number(o.from ?? 0), to = Number(o.to ?? duration);
    const file = o.out ? path.resolve(o.out) : path.join(renders, `range-${from}-${to}.mp4`);
    const page = await openPage();
    const enc = encoder(file, outFps);
    for (const t of framesIn(from, to)) await enc.write(await frameAt(page, t, true));
    await enc.end();
    console.log(file);
    return;
  }

  // ---- full render, cached per shot segment ----
  // Segment i covers [shot_i.start, shot_{i+1}.start). Its key covers every input that can change its pixels:
  // the shots active in that window, their code, lib/, assets/, style, meta, render settings, and the cues
  // those shots read during the last render (recorded by the runtime).
  const shots = [...tl.shots].sort((a, b) => a.start - b.start);
  // Everything in the project that can draw pixels, except per-shot code and the timeline (keyed per segment below).
  const notPicture = new Set(['renders', 'media', 'review', 'audio', 'shots', 'node_modules', '.git', 'timeline.json',
    'spec.md', 'brief.md', 'progress.md', 'licenses.json', 'CREDITS.md']);
  // Only lib/ code a page can load counts; the Python and audio tools don't change pixels.
  const shared = sha(hashTree(projectDir, notPicture), hashTree(libDir, new Set(['starter', 'starter-onetake']), /\.(m?js|css|glsl|json)$/), tl.meta,
    { scale, step, crf, preset, chromeArgs, png: o.png });
  const segments = shots.map((s, i) => {
    const start = s.start;
    const end = i + 1 < shots.length ? shots[i + 1].start : duration;
    const active = shots.filter(x => x.start < end && x.end > start);
    const code = active.map(x => readOr(path.join(projectDir, 'shots', `${x.id}.js`)));
    const staticKey = sha(shared, active, ...code, { start, end });
    const depsFile = path.join(cacheDir, `${s.id}.deps.json`);
    const deps = fs.existsSync(depsFile) ? readJSON(depsFile) : null;
    const cueIds = deps && deps.staticKey === staticKey ? deps.cues : (tl.cues || []).map(c => c.id);
    const cueKey = ids => sha(staticKey, (tl.cues || []).filter(c => ids.includes(c.id)));
    const file = path.join(cacheDir, `${s.id}-${cueKey(cueIds)}.mp4`);
    return { s, start, end, staticKey, depsFile, cueKey, file, frames: framesIn(start, end) };
  }).filter(seg => seg.frames.length > 0);

  const todo = segments.filter(seg => !fs.existsSync(seg.file));
  console.log(`${segments.length - todo.length}/${segments.length} shot segments reused, ${todo.length} to render: ${todo.map(x => x.s.id).join(', ') || 'none'}`);

  let firstMs = null;
  const queue = [...todo];
  const totalFrames = todo.reduce((n, seg) => n + seg.frames.length, 0);
  const worker = async () => {
    const page = await openPage();
    for (let seg = queue.shift(); seg; seg = queue.shift()) {
      const tmp = `${seg.file}.part.mp4`;
      const enc = encoder(tmp, outFps);
      await page.evaluate(() => window.__cuesUsed?.clear());
      const t0 = Date.now();
      for (const t of seg.frames) await enc.write(await frameAt(page, t, true));
      await enc.end();
      // Pages that don't record cue reads depend on every cue.
      const used = (await page.evaluate(() =>
        window.__cuesUsed ? [...new Set([...(window.__setupCues || []), ...window.__cuesUsed])] : null))
        ?? (tl.cues || []).map(c => c.id);
      const file = path.join(cacheDir, `${seg.s.id}-${seg.cueKey(used)}.mp4`);
      fs.renameSync(tmp, file);
      fs.writeFileSync(seg.depsFile, JSON.stringify({ staticKey: seg.staticKey, cues: used }));
      seg.file = file;
      if (firstMs === null) {
        firstMs = (Date.now() - t0) / seg.frames.length;
        const workers = Math.max(1, parseInt(o.workers, 10));
        console.log(`~${firstMs.toFixed(0)} ms/frame; estimated ${((firstMs * totalFrames) / 1000 / 60 / workers).toFixed(1)} min for this render`);
      }
      console.log(`rendered ${seg.s.id} (${seg.frames.length} frames)`);
    }
    if (page.__errors.length) console.log(`page errors:\n${page.__errors.join('\n')}`);
  };
  await Promise.all(Array.from({ length: Math.min(todo.length, Math.max(1, parseInt(o.workers, 10))) }, worker));

  const list = path.join(cacheDir, 'concat.txt');
  fs.writeFileSync(list, segments.map(seg => `file '${seg.file.replace(/'/g, "'\\''")}'`).join('\n'));
  const name = o.out ? path.resolve(o.out) : path.join(renders, preview ? 'preview.mp4' : `${slug}.mp4`);
  const silent = path.join(cacheDir, 'video-only.mp4');
  await ffmpeg(['-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', silent]);

  const mix = tl.audio?.out && path.join(projectDir, tl.audio.out);
  if (mix && fs.existsSync(mix)) {
    await ffmpeg(['-i', silent, '-i', mix, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k',
      '-ar', '48000', '-t', String(duration), '-movflags', '+faststart', name]);
  } else {
    await ffmpeg(['-i', silent, '-c', 'copy', '-movflags', '+faststart', name]);
    if (tl.audio?.out) console.log(`no audio yet (${tl.audio.out} missing); rendered picture only`);
  }
  console.log(name);
}

try {
  await run();
} catch (err) {
  console.error(err.message || err);
  process.exitCode = 1;
} finally {
  await browser.close();
  server.close();
}
