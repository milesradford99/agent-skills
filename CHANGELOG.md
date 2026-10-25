# Changelog

All notable changes are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/). Before 1.0, a minor version may change a skill's behavior.

## [Unreleased]

### Added

- `oss-mentor`: maintainer-partner skill with safety rules, decision rights, hobby/serious/org profiles, phase diagnosis, an upstream-contribution playbook and dated platform facts (verified 2026-10).
- `oss-design`: tiered product, tech and UI/UX design skill with convention-first guidance, drawn-theme variety, blind pairwise critique, a fresh-agent first-success test and accessibility gates.
- `video-director`: turns inspiration into finished videos. It locks the format first, asks at most 3 questions and shows three 10-second direction demos. It builds the video as code under a minimal render contract, so any renderer works. It defaults to continuous, one-take composition with on-screen words instead of slides and synthetic voiceover. Tuning notes become data edits on a shared cue sheet for picture and sound, and render caching is per segment. A blind 7-dimension reviewer loop runs before delivery. Includes a kit (`render.mjs`, `timeline.py`, `audio.py`, `qc.py`, `frames.py`, an optional shot runtime, and one-take and shot-based starters) and dated facts (verified 2026-10).
- Skills may carry an optional `references/` folder; the validator checks that every `references/...` path a SKILL.md mentions exists.
- Claude Code plugin marketplace (`milesradford-skills`) with one plugin per skill.
- Skill validator, tests and CI.
