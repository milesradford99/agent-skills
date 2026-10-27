#!/usr/bin/env python3
"""Timeline tools for seek(t) video projects. Standard library only.

    python3 lib/timeline.py check <slug>/timeline.json     validate; exit 1 on errors
    python3 lib/timeline.py frames <slug>/timeline.json    shots and cues with frame numbers
    python3 lib/timeline.py beats --bpm 128 --fps 30 [--offset 0.12] [--count 32] [--per-bar 4]

Beat times are computed absolutely (offset + n * 60 / bpm) and rounded to a frame once,
never by adding rounded frame counts, which drifts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:  # music.py sits beside this file; it validates audio.grooves without needing numpy
    import music
except ImportError:  # pragma: no cover
    music = None

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
# Comfortable reading speed for captions (subtitle-style guidance, approximate): CJK characters or Latin
# characters per second. Faster lines get a warning, because viewers can't read them and watch at once.
MAX_CPS_CJK = 9.0
MAX_CPS_LATIN = 17.0
KINDS = {"hook", "signature", "title", "end", "hit", "plain"}


def beat_grid(bpm: float, fps: float, offset: float = 0.0, count: int = 32, per_bar: int = 4) -> list[dict]:
    beat = 60.0 / bpm
    out = []
    for n in range(count):
        t = offset + n * beat
        out.append({"beat": n, "bar": n // per_bar, "downbeat": n % per_bar == 0, "t": round(t, 6), "frame": round(t * fps)})
    return out


def nearest_beat_error(t: float, bpm: float, offset: float) -> float:
    """Distance in seconds from t to the nearest beat on the grid."""
    beat = 60.0 / bpm
    n = round((t - offset) / beat)
    return abs(t - (offset + n * beat))


def check(tl: dict, project_dir: Path | None = None) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a timeline dict."""
    errors: list[str] = []
    warnings: list[str] = []
    meta = tl.get("meta", {})
    for key in ("width", "height", "fps", "duration", "seed"):
        if key not in meta:
            errors.append(f"meta.{key} is missing")
    if errors:
        return errors, warnings
    fps, duration = meta["fps"], meta["duration"]
    frame = 1.0 / fps

    shots = tl.get("shots")
    if shots is not None:
        if not shots:
            errors.append("shots is empty")
        ids = [s.get("id", "") for s in shots]
        for sid in ids:
            if not ID_RE.match(sid):
                errors.append(f"shot id '{sid}' must be lowercase letters, digits and hyphens")
        for sid in {i for i in ids if ids.count(i) > 1}:
            errors.append(f"shot id '{sid}' is used more than once")
        starts = [s.get("start", 0) for s in shots]
        if starts != sorted(starts):
            errors.append("shots must be sorted by start")
        covered = 0.0
        for s in sorted(shots, key=lambda s: s.get("start", 0)):
            start, end = s.get("start"), s.get("end")
            if start is None or end is None or end <= start:
                errors.append(f"shot '{s.get('id')}' needs start < end")
                continue
            if start > covered + 1e-9:
                errors.append(f"gap with no shot from {covered:g}s to {start:g}s")
            covered = max(covered, end)
            # Only projects built on lib/runtime.js need shots/<id>.js; a hand-written page has no shots/ folder.
            if project_dir is not None and (project_dir / "shots").is_dir() and not (project_dir / "shots" / f"{s['id']}.js").is_file():
                errors.append(f"shot '{s['id']}' has no shots/{s['id']}.js")
        if shots and covered + 1e-9 < duration:
            errors.append(f"no shot covers {covered:g}s to the end ({duration:g}s)")

    cues = tl.get("cues", [])
    cue_ids = [c.get("id", "") for c in cues]
    for cid in {i for i in cue_ids if cue_ids.count(i) > 1}:
        errors.append(f"cue id '{cid}' is used more than once")
    audio = tl.get("audio", {})
    for c in cues:
        t = c.get("t")
        if t is None or not 0 <= t <= duration:
            errors.append(f"cue '{c.get('id')}' time {t} is outside 0..{duration:g}s")
            continue
        kind = c.get("kind", "plain")
        if kind not in KINDS:
            errors.append(f"cue '{c.get('id')}' has unknown kind '{kind}'")
        if c.get("on_beat"):
            if "bpm" not in audio:
                errors.append(f"cue '{c['id']}' is on_beat but audio.bpm is not set")
            else:
                err = nearest_beat_error(t, audio["bpm"], audio.get("offset", 0.0))
                if err > frame + 1e-9:
                    errors.append(f"cue '{c['id']}' at {t:g}s is {err * fps:.1f} frames off the beat grid")
        if kind == "hook" and t > 0.5:
            warnings.append(f"hook cue at {t:g}s; aim for 0.5s or earlier on social")
        if kind == "signature" and not 0.6 * duration <= t <= 0.75 * duration:
            warnings.append(f"signature cue at {t:g}s is outside 60-75% of the runtime ({0.6 * duration:g}-{0.75 * duration:g}s)")
    if cues:
        last = max(c.get("t", 0) for c in cues)
        if duration - last < 0.8:
            warnings.append(f"only {duration - last:.2f}s after the last cue; hold the end 0.8-1.2s")

    for i, c in enumerate(tl.get("captions", [])):
        text, start, end = c.get("text", ""), c.get("start"), c.get("end")
        if start is None or end is None or end <= start:
            errors.append(f"caption {i} needs start < end")
            continue
        cjk = len(CJK_RE.findall(text))
        latin = len(re.sub(r"\s", "", text)) - cjk
        rate = cjk / MAX_CPS_CJK + latin / MAX_CPS_LATIN  # seconds needed to read it
        if rate > (end - start) + 1e-9:
            warnings.append(f"caption {i} at {start:g}s needs ~{rate:.1f}s to read but is on for {end - start:.1f}s")

    chapters = tl.get("chapters", [])
    starts = [c.get("start") for c in chapters]
    if any(t is None or not 0 <= t < duration for t in starts):
        errors.append(f"every chapter needs a start inside 0..{duration:g}s")
    elif starts != sorted(starts):
        errors.append("chapters must be sorted by start")

    if audio.get("grooves") and music is not None:
        try:
            music.resolve_grooves(tl)
        except ValueError as e:
            errors.append(str(e))

    if not audio.get("music") and not audio.get("no_music"):
        warnings.append("no music bed: set audio.music (lib/music.py composes one), "
                        "or audio.no_music with the user's reason")

    # "cue:<id>" references in shot params must point at real cues.
    for s in shots or []:
        for key, value in (s.get("params") or {}).items():
            if isinstance(value, str) and value.startswith("cue:") and value[4:] not in cue_ids:
                errors.append(f"shot '{s.get('id')}' param '{key}' refers to unknown cue '{value[4:]}'")
    return errors, warnings


def frames_table(tl: dict) -> str:
    fps = tl["meta"]["fps"]
    lines = ["kind   id                 start     frame   end       frame"]
    for s in tl.get("shots", []):
        lines.append(f"shot   {s['id']:<18} {s['start']:<9g} {round(s['start'] * fps):<7} {s['end']:<9g} {round(s['end'] * fps)}")
    for c in tl.get("cues", []):
        lines.append(f"cue    {c['id']:<18} {c['t']:<9g} {round(c['t'] * fps):<7} {c.get('kind', 'plain')}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "frames"):
        p = sub.add_parser(name)
        p.add_argument("timeline")
    b = sub.add_parser("beats")
    b.add_argument("--bpm", type=float, required=True)
    b.add_argument("--fps", type=float, required=True)
    b.add_argument("--offset", type=float, default=0.0)
    b.add_argument("--count", type=int, default=32)
    b.add_argument("--per-bar", type=int, default=4)
    args = ap.parse_args(argv)

    if args.cmd == "beats":
        print(json.dumps(beat_grid(args.bpm, args.fps, args.offset, args.count, args.per_bar)))
        return 0
    path = Path(args.timeline)
    tl = json.loads(path.read_text(encoding="utf-8"))
    if args.cmd == "frames":
        print(frames_table(tl))
        return 0
    errors, warnings = check(tl, path.parent)
    for w in warnings:
        print(f"WARN {w}")
    for e in errors:
        print(f"FAIL {e}")
    if errors:
        return 1
    print(f"OK {len(tl.get('shots', []))} shots, {len(tl.get('cues', []))} cues, {tl['meta']['duration']:g}s at {tl['meta']['fps']:g} fps")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
