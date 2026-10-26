# Pipeline

How a video is built as code: free to use any renderer, cheap to revise. All tools live in `references/kit/` and get copied to `video/lib/` once.

## Project layout

```text
video/
  lib/                 the kit (render.mjs, timeline.py, audio.py, qc.py, frames.py, runtime.js, starters); components/ if the user keeps any
  recipes/             directions the user chose to keep; _rejected/ for ones that didn't work
  preferences.md       the user's tastes, platform defaults, preflight results, budget
  node_modules/        playwright (npm i -D playwright; npx playwright install chromium)
  .gitignore           copied from kit/gitignore
  <slug>/
    index.html  timeline.json  spec.md  brief.md  progress.md  licenses.json
    style.json         optional: tuning values once the direction is locked
    *.js, shaders/     the renderer, in whatever shape the piece needs
    shots/<id>.js      only when using the shot runtime
    assets/            fonts/, images/, plates/ (generated, cached), data/
    audio/             music.wav, sfx/, mix.wav (mastered)
    media/raw/         footage originals, never modified
    renders/           cache/, stills/, preview.mp4, <slug>.mp4
    review/round-N/    qc.json, pack/, review.md
```

Start a project from the chosen direction's keyframe page. For a blank start, `lib/starter-onetake/` is a hand-written one-take canvas page with timed captions, and `lib/starter/` uses the shot runtime. Start from a recipe only for a series, a brand, or when the user asks. Commit after each version: `git -C video add -A && git -C video commit -m "v3: hook on the downbeat, warmer palette"`. If `video/` is inside the user's repo, ask once before committing there; otherwise `git init` it.

## Preflight

```sh
ffmpeg -hide_banner -version | head -1
ffmpeg -hide_banner -encoders | grep -E 'libx264|aac'
ffmpeg -hide_banner -filters | grep -E ' (drawtext|loudnorm|ebur128|blackdetect|freezedetect|showspectrumpic) '
node --version                     # 22+
npx playwright --version
blender --version | head -1        # only for 3D
python3 --version
nvidia-smi -L 2>/dev/null || ls /dev/dri 2>/dev/null   # GPU present?
fc-list : family | sort -u | head  # what fonts exist (bundle the ones you use anyway)
```

Run these through the user's login shell (`$SHELL -lic '...'`) if the agent's shell doesn't find a tool: PATH set in `~/.zshrc` or `~/.bashrc` often isn't loaded in agent shells, and the tool is already there. Record the results in `video/preferences.md` so the next video skips this. A missing tool gets one install line for the user to approve (for example `sudo apt-get install -y ffmpeg nodejs npm blender` on Ubuntu, `brew install ffmpeg node blender` on macOS). Then move on with the fallback route from SKILL.md.

## The render contract (page route)

Any page `render.mjs` can open is a valid renderer when it:
- exposes `window.seek(t)` that draws the complete frame for time `t` (it may be async);
- sets `window.DURATION`, and `window.__ready = true` once fonts and assets have loaded (or `window.__error` on failure);
- is deterministic: the frame is a pure function of `t`, whatever was drawn before;
- reads cue times from `timeline.json` rather than hard-coding them, so picture and sound stay in step.

Forbidden inside `seek`: `Date.now`, `performance.now`, `setTimeout`, `setInterval`, `requestAnimationFrame` loops, CSS transitions and animations, unseeded `Math.random`, live audio analysis, HTML `<video>` playback. Precompute anything expensive (audio envelopes, physics, particle paths) into JSON under `assets/data/` with a script, and read it by frame. Simulations must be re-run from a seed up to `t`, or precomputed.

Everything else is your choice: canvas, WebGL with your own shaders, SVG, DOM, three.js, or a custom engine. For WebGL, draw the whole frame in `seek` and create the context with `preserveDrawingBuffer: true`.

**Two shapes, chosen per piece:**
- **One renderer for the whole piece** (`starter-onetake/`): a single shot spanning the timeline; one continuous world and camera. The default for continuous and one-take work. It caches as one segment, so use `--from/--to` and `--at` for fast checks.
- **Shot runtime** (`starter/`, `runtime.js`): `index.html` calls `mount()`; each `shots/<id>.js` exports `render(ctx)` and optionally `setup(ctx)`. Overlapping shots render together for transitions. `ctx` gives `t`, `p`, `T`, `frame`, `params` (with `"cue:<id>"` references resolved), `style`, `cue(id)`, `ease(name)`, `rng()` and `rngAt(key)`. Each shot segment caches separately, and the cache records which cues each shot read. Use it when the piece really is separable scenes.

Optional extras `render.mjs` understands: `window.__missingFonts` (it refuses to render when non-empty) and `window.__cuesUsed` (finer cache keys).

## Commands

```sh
cd video
python3 lib/timeline.py check <slug>/timeline.json           # before every render
node lib/render.mjs --project <slug> --check                 # after changing how frames are drawn
node lib/render.mjs --project <slug> --at 0.4,6.5,9.5        # key stills only
node lib/render.mjs --project <slug> --scale 0.5 --step 2    # fast motion preview
node lib/render.mjs --project <slug> --from 6 --to 7.5       # one moment
python3 lib/audio.py sfx impact <slug>/audio/sfx/impact.wav  # whoosh, riser, impact, click, subdrop
python3 lib/music.py <slug>/timeline.json                    # compose the score from the cues (needs numpy)
python3 lib/audio.py mix <slug>/timeline.json                # cues + music + ducking, mastered to audio.out
node lib/render.mjs --project <slug>                         # full render, picture cached per segment, audio muxed
python3 lib/qc.py <slug>/renders/<slug>.mp4 <slug>/timeline.json --out <slug>/review/round-1/qc.json
python3 lib/frames.py review <slug>/renders/<slug>.mp4 <slug>/timeline.json <slug>/review/round-1/pack
```

`render.mjs` prints how many segments it reused and the measured ms per frame with an estimate. Frames are captured as JPEG (quality 95) by default, about 5× faster than PNG on textured pages; pass `--png` for lossless capture of flat graphics. Workers default to half the CPU cores; more than that competes for CPU and slows the render. On a machine without a GPU, WebGL runs on SwiftShader (the default flags); pass `--chrome-arg=...` to change them. Changing the Python or audio tools in `lib/` doesn't invalidate the picture cache.

## Iteration rules

1. **Classify the note before touching anything.** A tuning note (timing, words, colour, size, easing) becomes a data edit (see the table in `spec-template.md`). A note about the idea, the impact or the flow ("it feels like slides", "the middle is flat") is a code change: redesign the beat or the transition, don't nudge numbers.
2. **Change one thing per note, and nothing else.** Don't tidy, rename or restyle in the same edit.
3. **Re-render the smallest thing that proves the fix:** a still (`--at`), then a range (`--from/--to`), then the full render, which reuses every unchanged segment.
4. **Retiming goes through cues.** Move the cue; picture and sound follow. Snap music-driven cues with `timeline.py beats` and `on_beat: true`.
5. **Commit each version** so a regression is a `git checkout` away. Keep every rendered version in `renders/` until delivery; the best one may not be the last.
6. **Keep context small.** Read script summaries, not logs. Look at a contact sheet before individual frames, and at individual frames only where the sheet shows a problem.

## Reuse

- Reused parts pull new videos toward the old ones, so reuse is for a series, a brand, or "like last time". For a new direction, write fresh code.
- After delivery, offer once to keep what worked: a reusable part becomes a component in `video/lib/components/`; the direction becomes a recipe (`spec.md`, `style.json` if any, the renderer, and a one-line description of when to use it). Write `video/recipes/INDEX.md` lines as `name — style, form, what it's good for`.
- Never promote something the user disliked; log it in `recipes/_rejected/` with the reason instead.

## 3D route (Blender)

- Write the scene as a bpy script in `<slug>/blender/scene.py` that reads `timeline.json` for timing (cue times become keyframes at `round(t * fps)`) and `style.json` for colours.
- Test before committing to a sequence: `blender -b -P blender/scene.py -- --still 6.5 --out renders/stills/` and time it. Extrapolate per-frame time × frames. Over ~30 minutes, propose Eevee on GPU, fewer samples, shorter shots, or a three.js page instead, before rendering.
- Render frames to `renders/frames/####.png` with `blender -b -P blender/scene.py -- --render`, then encode: `ffmpeg -framerate 24 -i renders/frames/%04d.png -c:v libx264 -crf 18 -pix_fmt yuv420p renders/picture.mp4`.
- Use Cycles for headless rendering unless the machine has a working GPU context for Eevee. Avoid Grease Pencil objects in background renders. Set the engine on every scene the script creates, not just the current one.
- Re-render only frame ranges whose shots changed (`--frames a-b`), mirroring the page cache.

## Footage route (MAD, montage, trailer, reel)

1. **Ingest.** Copy sources into `media/raw/` untouched, with their origin in `licenses.json`. Make constant-frame-rate proxies for analysis: `ffmpeg -i in.mp4 -vf scale=-2:540,fps=24 -c:v libx264 -crf 23 -an media/proxy/<name>.mp4`.
2. **Shots.** Detect cuts with PySceneDetect (`scenedetect -i proxy.mp4 detect-adaptive list-scenes save-images -n 1`), or TransNetV2 for fast-cut anime and flashes.
3. **Shot log.** Tag one to three keyframes per shot with the vision model into `assets/data/shots.json`: shot size, subject role (never a real person's identity), motion energy, direction of motion, dominant colours, on-screen text or logos, quality flags. Measure motion energy from frame differences or optical flow and store it as a number. Tag downscaled frames (about 768 px wide) to keep cost low.
4. **Music grid.** Beats and downbeats with Beat This! (`beat_this song.wav`); lyric word times with WhisperX, corrected against the official lyrics. Write them as cues in `timeline.json`.
5. **Assignment.** Choose cut points on downbeats and lyric hits, not every beat. Give each slot a wanted energy and shot size; density rises into the chorus; the strongest motion lands on the drop; lyric syncs where the words allow. Write `cuts.json`: `[{ "src": "media/raw/a.mp4", "in": 12.48, "out": 13.31, "at": 4.0, "speed": 1.0, "fx": [] }]`.
6. **Render.** Re-encode every cut (`trim`, `setpts`, `concat` in one `filter_complex`, integer frame math); never stream-copy cuts. Overlays (titles, lyrics) are rendered by the page route as transparent PNG frames or a separate pass and composited with `overlay`.
7. **Hand-off.** Export OpenTimelineIO (`opentimelineio` Python package) from `cuts.json` so an editor can finish in Resolve.

Revisions are edits to `cuts.json` and cue times, re-rendered by ffmpeg in seconds.

## Audio route

- **Music, by default.** Use the user's own or licensed track if they have one. Otherwise `lib/music.py` composes a bed in seconds from `audio.bpm`, `audio.mood` and the cues (or `audio.sections`): pad, soft arpeggio, sub bass and light percussion in a synthetic room, with a held beat of near-silence before the signature cue. It's dependable, not a film score. For a richer score, write notes with `pretty_midi` following the same sections and render them through FluidSynth or sfizz with CC0 or attributed samples (VSCO-2 CE, Salamander piano), then `pedalboard`; sampled piano holds up, sampled strings and choir stay demo-quality. Set `audio.music`, keep `music_gain_db` around −4 to −8 so captions' SFX sit on top, and run `audio.py mix`.
- **SFX.** `audio.py sfx` covers whooshes, risers, impacts, clicks and sub drops. The mixer aligns each sound's transient, not its file start, to the cue time.
- **Words.** Default to on-screen type and captions (`captions` in `timeline.json`), timed to cues. Voiceover only when the user asks: their own recording, or Kokoro (local, Apache-2.0); add a `duck` range under each line, and keep captions on.
- **Generated music or voice from a paid API** is spend: estimate and ask first.
- **Delivery.** `audio.py mix` masters to the timeline's `lufs` and `true_peak` (default −14 LUFS, −1 dBTP for web) with two-pass loudnorm, a final 4×-oversampled limiter for sharp transients, and 48 kHz output. Keep the platform's target; a soundtrack too thin to reach it needs music, not a lower target.

## Generated plates

When a direction needs imagery code can't draw, generate it once (on the user's yes; see `originality.md`), save it under `assets/plates/`, log model, prompt, seed and date in `licenses.json`, and composite it in the page. Plates are inputs, like fonts: the cache tracks them and nothing regenerates them on render.

## licenses.json

```json
[
  { "path": "audio/music.wav", "source": "composed in audio/score.py", "license": "original", "attribution": null },
  { "path": "assets/fonts/Fraunces.woff2", "source": "Google Fonts", "license": "OFL-1.1", "attribution": null },
  { "path": "media/raw/trailer-01.mp4", "source": "https://…", "license": "user-provided, rights not verified", "attribution": "© Publisher" },
  { "path": "assets/plates/sky.png", "source": "generated", "license": "per provider terms", "model": "…", "prompt": "…", "seed": 7, "date": "2026-10-25" }
]
```

Generate `CREDITS.md` from it at delivery, with AI-generated elements labeled.
