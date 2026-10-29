# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/). Before 1.0, a minor version may change a skill's behavior.

## [Unreleased]

### Added

- `oss-mentor`: maintainer-partner skill with safety rules, decision rights, hobby/serious/org profiles, phase diagnosis, an upstream-contribution playbook and dated platform facts (verified 2026-10).
- `oss-design`: tiered product, tech and UI/UX design skill with convention-first guidance, drawn-theme variety, blind pairwise critique, a fresh-agent first-success test and accessibility gates.
- `video-director`: turns inspiration into finished videos. It locks the format first, asks at most 3 questions and shows three 10-second direction demos. It builds the video as code under a minimal render contract, so any renderer works. It defaults to continuous, one-take composition with on-screen words instead of slides and synthetic voiceover. Tuning notes become data edits on a shared cue sheet for picture and sound, and render caching is per segment. A blind 7-dimension reviewer loop runs before delivery. Includes a kit (`render.mjs`, `timeline.py`, `audio.py`, `qc.py`, `frames.py`, an optional shot runtime, and one-take and shot-based starters) and dated facts (verified 2026-10).
- `video-director`, after its first real use (a 3:42 explainer):
  - The user confirms what the video says: a story card (promise, takeaways, every on-screen line, numbers with sources, what's left out) ships with the direction demos, and the build waits for it. The rough cut is a real checkpoint for pieces over 60 s or that explain, argue or sell.
  - An audience pass: a fresh agent plays 2–3 target viewers, one of them skeptical, on the script and the rough cut. It reports where they'd drop off, which takeaways land, and what feels preachy or untrue.
  - Music by default: a new `music.py` composes a bed that follows the cues. Missing music is a QC warning, and lowering the loudness target to pass QC is ruled out.
  - Token budget: images are inspected by short-lived subagents rather than the main conversation, and the review pack is capped at about 20 images whatever the length. Round-2 A/B compares paired stills instead of two full packs.
  - Kit:
    - JPEG frame capture by default (about 5× faster on textured pages).
    - Workers default to half the cores.
    - Tool changes no longer invalidate the picture cache.
    - A final 4×-oversampled limiter for click-heavy mixes.
    - Frozen picture is a warning, not a failure.
    - Caption reading-speed checks.
    - New `frames.py tile` and `pair` subcommands.
  - Preflight checks the login shell's PATH before reinstalling tools.
  - Directions are five sets of 3 keyframes (hook, key moment, end), not three 10-second demo videos. One is led by the references, two come from random draws, one is a deliberate extreme and one is a best-in-class conventional take. A 10-second motion test is rendered only for the chosen direction, and only when its appeal depends on motion.
- `video-director` 0.2.0, after analysing a code-made rhythm lesson (9½ min, synthesized grooves locked to an on-screen beat ruler):
  - A Lesson format for chaptered explainers (3–10 min): a cold open, chapters that each add one concept, teaching pages that alternate with full examples, and a persistent on-screen instrument drawn from data.
  - `music.py` plays the content's own patterns: `audio.grooves` windows with 13 presets (heartbeat, march, waltz, rock, disco, funk, trap, reggae, shuffle, bossa, tresillo, dembow, 7/8) or custom step lanes, with swing and per-window tempo. Every hit is written to `audio/events.json` so the picture draws from the same data. The bed drops out under each window.
  - A fact check before the audience pass for anything that explains or teaches: a fresh agent rates every claim ok, overstated, unsupported or wrong, and the gate allows no wrong or unsupported line on screen.
- `video-director` 0.3.0, recorded sound effects (method adapted from [vibe-motion/sound](https://github.com/vibe-motion/sound)):
  - New `sfx.py`: searches Freesound through its official API, re-ranks relevance results by downloads and shows votes, license and the uploader's description; `get` downloads HQ previews in parallel, converts them to 48 kHz WAV and logs source, license and credit in `licenses.json`, refusing BY-NC and Sampling+ unless the piece is non-commercial; `measure` reports length, transient, ring and energy band so a popular clip is checked before it's trusted.
  - SKILL.md prefers recorded effects picked on evidence (downloads, rating count over average, the description as listening) over synthesis, which stays as the fallback without a key and as a sub layer.
  - The mixer takes a list of layers per cue (`{path, gain_db, len}`), aligns each layer's transient on the cue for any audio format, and trims and fades a long ring. `timeline.py check` validates layers and warns when a Freesound clip isn't in `licenses.json`.
  - The kit's gitignore covers downloaded audio under `audio/`, the API key file and the search index.
  - `timeline.py check` validates grooves and the new optional `chapters` table.
- Skills may carry an optional `references/` folder; the validator checks that every `references/...` path a SKILL.md mentions exists.
- Claude Code plugin marketplace (`milesradford-skills`) with one plugin per skill.
- Skill validator, tests and CI.
