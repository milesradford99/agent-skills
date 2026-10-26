# Spec template

## Story card (phase 2, shown to the user with the demos)

What the video *says*, on one screen, in the final language. The user approves it or edits lines; the build waits for that.

```markdown
# <working title>

**Promise:** <one sentence: what a viewer will understand or feel by the end>
**For:** <the target viewer in one line, e.g. "a 45-year-old patient in a county town who has noticed fees changed">
**Takeaways:** 3–5 things they can say afterwards in their own words
**Stance:** <the view the piece takes, and the one honest caveat it includes>

| Time | Beat | On-screen words (final language) | Picture |
|---|---|---|---|
| 0:00–0:08 | Hook | ... | ... |
| ... | ... | ... | ... |

**Key moment:** <timecode, what happens, why it's the payoff>
**Numbers:** every figure on screen, each with its source (sources.md row)
**Left out on purpose:** <topics or claims not covered, and why>
**Length:** <m:ss> · **Music:** <composed, mood> · **Voice:** none
**Audience read:** <the audience pass summary: who stays, who drops off where, what confused or rang false, what was fixed>
```

Keep it to what the user needs to judge content; craft details belong in the spec below.


The spec turns the chosen direction into a brief the producer can check against frames, and the reviewer can score against. Write it to `video/<slug>/spec.md`. Every requirement is a number, a time or a named thing; "feels premium" can't be checked against a frame, "titles snap in 10 frames on `cubic-bezier(.7,0,.2,1)`" can.

## spec.md

```markdown
# <title>

## Role and bar
You are director, motion designer, engineer and sound designer. Aim for the most recognizable, striking
expression of <style>, at the level of <2–4 benchmark studios or works the user would recognize>.
Emulate their qualities (named below); never copy their work. A polished result that still looks like a
template fails this brief.

## Proposition
<One sentence: what the viewer should feel or know at the end.>

## Output
<W×H>, <fps> fps, exactly <frames> frames (<duration> s), H.264 yuv420p BT.709, 48 kHz stereo AAC,
<-14> LUFS integrated, true peak ≤ <-1> dBTP. Fonts bundled in assets/fonts/.

## Beats (seconds)
| Time | Beat | What's on screen | Sound |
|---|---|---|---|
| 0.0–0.5 | Hook | <the first image, already moving> | <hit or texture> |
| … | … | … | … |
| <60–75% of runtime> | Signature moment | <the one thing people remember> | <silence before, loudest on it> |
| last 0.8–1.2 | End hold | <end card or final image> | <tail> |

## Signature moment
<One moment only. What happens, at which cue, and why it's the payoff. Often "the end is the start, changed".>

## Continuity
<How each beat becomes the next: the camera path, the object or shape that carries over, match cuts or morphs.
Say "one take" if it is one. List every hard cut and why it's there (rhythm, a hit, a reset). A beat that
only appears and disappears is a slide; redesign it.>

## Words on screen
<Every line the viewer reads, with its cue, its treatment (kinetic title, caption, label) and minimum size.
No voiceover unless the user asked for one.>

## Style rules
<Copied and adapted from styles.md: frame rate or stepping, easing curves, stagger in frames,
parallax ratios, palette (hex), type families and minimum sizes, texture.>

## Avoid
<The style's failure list, the AI-video tells from originality.md, and the user's own dislikes.>

## Camera and composition
<Angles, lens or projection, moves per beat, safe areas for the platform.>

## Sound plan
<Music: the user's track, or composed with lib/music.py (mood, tempo, sections that follow the cues).
No music only if the user said so. The cue list with each SFX, and the one place silence is used.
Voiceover and ducking only if the user asked for a voice.>

## Production steps
1. Key stills at the hook, signature moment and end card; iterate until nothing looks generic.
2. Low-res motion pass of the whole piece.
3. Sound built on the same cues.
4. Full render, QC, review loop.

## Checks before delivery
<What qc.py will measure, plus style-specific checks: e.g. "camera moves in whole pixels only",
"no frame without the accent colour after 2.0 s", "every caption onset within 1 frame of its word".>
```

Fill the beat table from the form's arc in `formats.md`. Keep the hook inside 0.5 s for social and 1–2 s for long-form.

## timeline.json

The single source of truth for timing. Picture and sound both read it.

```json
{
  "meta": {
    "title": "Isometric city",
    "width": 1920, "height": 1080, "fps": 30, "duration": 10.0,
    "seed": "Q2xhdWRlIGNpdHkgc2VlZA",
    "background": "#0f1115"
  },
  "audio": {
    "bpm": 120, "offset": 0.0,
    "music": "audio/music.wav", "mood": "warm", "music_gain_db": -4,
    "sections": [{ "start": 0, "end": 0.4, "energy": 0 }, { "start": 0.4, "end": 4.5, "energy": 1 },
                 { "start": 4.5, "end": 6.5, "energy": 2 }, { "start": 6.5, "end": 8.6, "energy": 3 }, { "start": 8.6, "end": 10, "energy": 1 }],
    "duck": [{ "start": 2.0, "end": 4.5, "db": -8 }],
    "out": "audio/mix.wav",
    "lufs": -14, "true_peak": -1
  },
  "shots": [
    { "id": "tiles",     "start": 0.0, "end": 2.2, "params": { "rows": 8, "wave": "cue:hook" } },
    { "id": "buildings", "start": 2.0, "end": 5.0, "params": { "count": 14, "overshoot": 0.08 } },
    { "id": "life",      "start": 5.0, "end": 8.0, "params": { "parallax": [1, 0.8, 0.6] } },
    { "id": "reveal",    "start": 8.0, "end": 10.0, "params": { "title": "Harbor City" } }
  ],
  "cues": [
    { "id": "hook",      "t": 0.4,  "kind": "hook",      "sfx": "audio/sfx/impact.wav", "gain_db": -4, "on_beat": true },
    { "id": "grow",      "t": 2.0,  "kind": "hit",       "sfx": "audio/sfx/riser.wav",  "gain_db": -10 },
    { "id": "signature", "t": 6.5,  "kind": "signature", "sfx": "audio/sfx/impact.wav", "gain_db": -2, "on_beat": true },
    { "id": "title",     "t": 8.6,  "kind": "title",     "sfx": "audio/sfx/click.wav",  "gain_db": -8 }
  ],
  "qc_allow": [
    { "kind": "freeze", "start": 9.0, "end": 10.0, "why": "end card hold" }
  ]
}
```

Rules, all checked by `timeline.py check`:
- `meta` has `width`, `height`, `fps`, `duration` and `seed`.
- Shot ids are unique, lowercase letters, digits and hyphens, and each has `shots/<id>.js`. Shots are sorted by `start`, the first starts at 0, there are no gaps, and the last ends at or after `duration`. Shots may overlap for transitions; both render during the overlap, later shots on top.
- Cue ids are unique and `0 ≤ t ≤ duration`. A cue with `"on_beat": true` must sit within one frame of the beat grid from `audio.bpm` and `audio.offset`.
- `kind` is one of `hook`, `signature`, `title`, `end`, `hit` or `plain`. The checker warns when the hook is later than 0.5 s, when the signature moment is outside 60–75% of the runtime, or when less than 0.8 s follows the last cue.
- In shot code, read cue times with `ctx.cue("hook")`, never a copied number. A param written as `"cue:hook"` is a reference to that cue.
- `qc_allow` lists intentional black, frozen or silent stretches so QC doesn't flag them.

`captions` (optional) holds on-screen words with times: `[{ "start": 0.5, "end": 1.9, "text": "Start with a line." }]`. Keep each line's start on a cue or beat so words and sound land together. Density: at most 3 live lines on screen, older lines dimmed or cleared, at least 44 px at 1080p, and on screen long enough to read (`timeline.py check` warns above about 9 CJK or 17 Latin characters per second).

`audio.sections` (optional) sets the score's energy, 0 (rest) to 3 (full); without it `music.py` derives an arc from the hook and signature cues. `audio.no_music` holds the user's reason when they don't want music; `timeline.py check` warns when neither it nor `audio.music` is set.

A one-take piece usually has a single shot spanning the whole timeline and draws everything in one renderer; that's the normal case, not a workaround. Footage forms use the same `meta`, `audio` and `cues`, and replace `shots` with a cut list (see `pipeline.md`).

## style.json (optional)

Once the direction is locked, put here the visual values a note like "warmer", "faster" or "bolder type" should change. A hand-written page can read it or keep a small constants block at the top of its script; either way, tuning values live in one obvious place.

```json
{
  "palette": { "bg": "#0f1115", "ink": "#f4efe6", "accent": "#ff5a36", "mid": "#3a4a5c", "soft": "#c9b79c" },
  "fonts": ["Fraunces", "IBM Plex Mono"],
  "ease": {
    "enter": [0.16, 1, 0.3, 1],
    "exit": [0.7, 0, 0.84, 0],
    "snap": [0.7, 0, 0.2, 1]
  },
  "timing": { "stagger_frames": 3, "move_frames": 12, "hold_frames": 18 },
  "step_fps": 0,
  "type": { "min_px": 48, "title_px": 160, "tracking": -0.02 }
}
```

- Palette keys become CSS variables (`--bg`, `--ink`) and are available as `ctx.style.palette` in shot code.
- Every family in `fonts` must be declared with `@font-face` from `assets/fonts/`. The render refuses to run if one doesn't load.
- `ease` entries are cubic-bezier control points; use them through `ctx.ease("enter")`.
- `step_fps` above 0 quantizes animation time (12 for cut paper, 12 for on-twos at 24 fps); 0 means smooth.
- Add keys for the values that notes actually touch. Don't parameterize everything up front: it freezes the first idea.

## Mapping notes to edits

| Note | First place to change |
|---|---|
| "Faster" / "slower" | `style.timing`, shot `start`/`end`, cue times |
| "Hit it on the drop" | The cue's `t` (snap to the beat grid with `timeline.py beats`) |
| "Warmer" / "darker" | `style.palette` |
| "Bigger, bolder type" | `style.type`, `style.fonts` |
| "Less bouncy" | `style.ease` |
| "Change the words" | `captions` or shot `params` |
| "Cut that part" | Remove or shorten the shot, retime the following cues |
| "Make the ending land" | The `signature` or `end` cue, the end hold, and the sound plan |

These are tuning notes. Notes about the idea itself ("the middle is boring", "it doesn't land", "it feels like slides") are expected to change code: redesign the beat, the transition or the signature moment rather than nudging numbers.
