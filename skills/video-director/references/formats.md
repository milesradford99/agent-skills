# Formats

Lock the format before any style work. Show the user the one-liners, never the internal names alone. Durations and arcs are working defaults from craft practice, not sourced standards; adjust them to the platform and the user's material.

Every generated form below defaults to continuous composition (beats that transform into each other, often one take) with words carried by on-screen type and captions. None of them asks about voiceover; add one only when the user asks or brings their own recording.

## Picking the top 3 to show

| Inspiration contains | Lean toward |
|---|---|
| A song file and links to anime, game or film trailers | MAD/AMV, lyric video, trailer |
| A song file and nothing else | Lyric video, visualizer, motion graphics |
| The user's own clips or photos | Montage, social reel, trailer |
| Screenshots or a product URL | Product promo, motion graphics, explainer |
| A script, article or topic | Explainer, motion graphics, data story |
| Numbers, a CSV or a chart | Data story, explainer, motion graphics |
| A story premise or characters | Animated short, 3D piece, trailer |
| A reference video | The reference's own form first, then its two nearest neighbours |

## The 12 forms

### Motion graphics / kinetic type
- **For users:** "Designed shapes, type and icons, animated."
- **Needs:** copy or a theme; brand kit if any.
- **Arc:** hook within 0.5 s → build → one signature moment at 60–75% → resolve to a title or end card held 0.8–1.2 s.
- **Default spec:** 16:9 1920×1080, 30 fps (or the style's own rate), 10–30 s.
- **Toolchain:** HyperFrames if installed, else a `seek(t)` page.
- **Extra question:** "Any exact words that must appear?"

### Explainer
- **For users:** "An idea made clear step by step, often narrated."
- **Needs:** script or topic, facts, sources for claims.
- **Arc:** question or tension → 3–5 steps, each one visibly growing out of the last (the diagram from step 2 becomes the stage for step 3) → the whole picture → one call to action.
- **Default spec:** 16:9, 30 fps, 45–90 s; words as kinetic captions, no voice.
- **Toolchain:** one `seek(t)` page with a continuous camera over a single evolving diagram or world, or Manim for math.
- **Extra question:** "What's the one thing a viewer should understand by the end?"

### Product promo / demo
- **For users:** "Your real product screens, with zooms, callouts and a payoff."
- **Needs:** screenshots, URL or a build; logo; one-line value proposition.
- **Arc:** problem in one beat → product reveal → 2–3 features shown in one continuous flight through the real UI (the camera moves between features instead of cutting to new cards) → logo and call to action.
- **Default spec:** 16:9 plus a 9:16 cut, 30 fps, 15–45 s.
- **Toolchain:** `seek(t)` page rebuilding the real UI in HTML, or screenshots with camera moves; never invented UI.
- **Extra question:** "What should viewers do at the end (site, download, waitlist)?"

### Animated short film
- **For users:** "Characters and a small story, in 2D or 3D."
- **Needs:** premise, or the subject to dramatize.
- **Arc:** setup → disruption → attempt → turn → resolution with an image that echoes the opening changed.
- **Default spec:** 16:9, 24 fps, 30–120 s; original score.
- **Toolchain:** `seek(t)` page (2D, WebGL allowed) or Blender (3D); Python score and SFX.
- **Extra question:** "Music and sound with any words on screen (recommended), or voiced dialogue?"

### 3D piece
- **For users:** "Objects, products or a small world, rendered in 3D."
- **Needs:** concept; product model or photos if it's a real product.
- **Arc:** reveal → orbit or journey → hero hold.
- **Default spec:** 16:9, 24–30 fps, 10–30 s.
- **Toolchain:** Blender headless after a one-frame test and a measured per-frame time; three.js on a page as the fallback.
- **Extra question:** none usually; ask for a model file only for a real product.

### MAD / AMV / fan edit
- **For users:** "Existing anime, game or film footage cut tightly to a song."
- **Needs:** the footage and the song, plus a rights answer.
- **Arc:** follows the song: intro establishes the world → verse builds with rising cut density → chorus or drop carries the strongest motion and lyric syncs → outro lands on a held image.
- **Default spec:** song length or the user's cut; source frame rate; 16:9.
- **Toolchain:** shot detection, a tagged shot log, Beat This! beats, WhisperX lyric times, an ffmpeg cut list, OTIO export.
- **Extra question:** "Where do the footage and song come from: your files, official trailers you want me to fetch (YouTube's Terms forbid downloading), or something else?"

### Montage / recap
- **For users:** "Your clips or photos, paced to music."
- **Needs:** clips or photos; a song or permission to compose one.
- **Arc:** opening image → chronological or thematic blocks → peak → closing image.
- **Default spec:** 16:9 or 9:16, 30–90 s.
- **Toolchain:** ffmpeg cut list plus page-rendered titles; photos get camera moves.
- **Extra question:** "Use a song you have, or should I compose one?"

### Trailer / teaser
- **For users:** "Tension that builds to a reveal, with title cards."
- **Needs:** footage or a concept; the title and date.
- **Arc:** quiet open → world → stakes → accelerating montage → silence → title hit → button (one last beat).
- **Default spec:** 2.39:1 letterbox inside 16:9, 24 fps, 60–120 s (teaser 15–30 s).
- **Toolchain:** ffmpeg cut list with page-rendered title cards and a composed score with risers and hits.
- **Extra question:** "What's the title and release line?"

### Lyric video
- **For users:** "A song's words animated in time with it."
- **Needs:** the song and official lyrics.
- **Arc:** follows the song's structure; the chorus gets the signature treatment.
- **Default spec:** song length, 16:9, 30 fps.
- **Toolchain:** WhisperX word times corrected against the lyrics file, then a `seek(t)` page.
- **Extra question:** "Is this the official lyrics file, and is the song yours or licensed?"

### Data story
- **For users:** "Charts that animate to make one clear point."
- **Needs:** the real numbers and their source.
- **Arc:** the claim → context → the reveal chart → what it means, as one chart that keeps transforming (axes rescale, bars become points, the highlight travels) rather than a series of separate charts.
- **Default spec:** 16:9, 30 fps, 30–60 s.
- **Toolchain:** `seek(t)` page with SVG or D3; numbers read from the data file, never typed in by hand.
- **Extra question:** "What's the one point the numbers should make?"

### Social reel / captions
- **For users:** "Vertical, captioned, with a hook in the first second."
- **Needs:** clips or a script.
- **Arc:** hook (≤1 s) → payoff promise → 3 fast beats → loop-friendly end.
- **Default spec:** 9:16 1080×1920, 30 fps, 15–60 s; captions inside the safe area.
- **Toolchain:** ffmpeg plus page-rendered captions, or a full page render.
- **Extra question:** "Talking to camera (your footage), or visuals with text?"

### Visualizer / generative loop
- **For users:** "Abstract visuals driven by the music."
- **Needs:** the song.
- **Arc:** none; energy follows the audio envelope, and the end frame matches the first for a seamless loop.
- **Default spec:** 1:1 or 16:9, 30–60 fps, song length or a 10–20 s loop.
- **Toolchain:** WebGL `seek(t)` page reading precomputed audio envelopes from JSON (never live analysis).
- **Extra question:** "A loop for social, or the full song?"

## Platform defaults

| Platform | Aspect and size | Length | Notes |
|---|---|---|---|
| TikTok, Reels, Shorts | 9:16, 1080×1920 | 15–30 s default | Keep text and faces out of the bottom ~20% and the right-hand icon column |
| YouTube | 16:9, 1920×1080 or 3840×2160 | Any | MP4, H.264 High, yuv420p, BT.709, 48 kHz AAC, fast start |
| X, LinkedIn | 16:9 or 1:1 | ≤60 s | Captions burned in; many viewers watch muted |
| Presentation or site | 16:9 | Any | Ask whether it should loop |
