#!/usr/bin/env python3
"""Technical QC of a rendered video against its timeline. Needs ffmpeg and ffprobe.

    python3 lib/qc.py <slug>/renders/<slug>.mp4 <slug>/timeline.json [--out <slug>/review/round-1/qc.json]

Checks resolution, frame rate (and variable frame rate), duration, codec, pixel format, audio format,
integrated loudness and true peak, plus true-black stretches over 0.25 s, frozen stretches over 2 s and silences over 1 s not listed in qc_allow.
Prints a one-line summary per failure; exit 1 if anything failed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def analyze(path: Path, has_audio: bool) -> str:
    args = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
            # Only true black (luma under 2%) for 0.25 s, and holds over 2 s: dark designs and short holds are normal.
            "-vf", "blackdetect=d=0.25:pix_th=0.02,freezedetect=n=-60dB:d=2"]
    if has_audio:
        args += ["-af", "ebur128=peak=true,silencedetect=n=-50dB:d=1"]
    args += ["-f", "null", "-"]
    return subprocess.run(args, capture_output=True, text=True).stderr


def parse_events(log: str) -> dict:
    """Pull black, freeze and silence intervals and the loudness summary out of ffmpeg's stderr."""
    black = [(float(a), float(b)) for a, b in re.findall(r"black_start:\s*([\d.]+)\s+black_end:\s*([\d.]+)", log)]
    fs = [float(x) for x in re.findall(r"freeze_start:\s*([\d.]+)", log)]
    fe = [float(x) for x in re.findall(r"freeze_end:\s*([\d.]+)", log)]
    ss = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", log)]
    se = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", log)]
    # A freeze or silence still running at the end of the file has a start but no end.
    freeze = [(a, fe[i] if i < len(fe) else None) for i, a in enumerate(fs)]
    silence = [(max(0.0, a), se[i] if i < len(se) else None) for i, a in enumerate(ss)]
    summary = log[log.rfind("Summary:"):] if "Summary:" in log else ""
    lufs = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summary)
    peak = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    to_num = lambda m: (float("-inf") if m.group(1) == "-inf" else float(m.group(1))) if m else None  # noqa: E731
    return {"black": black, "freeze": freeze, "silence": silence, "lufs": to_num(lufs), "true_peak": to_num(peak)}


def allowed(kind: str, start: float, end: float | None, allow: list[dict], duration: float) -> bool:
    end = duration if end is None else end
    return any(a.get("kind") == kind and a["start"] - 0.05 <= start and end <= a["end"] + 0.05 for a in allow)


def evaluate(info: dict, events: dict, tl: dict) -> list[dict]:
    meta, audio = tl["meta"], tl.get("audio", {})
    fps, duration = meta["fps"], meta["duration"]
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    checks: list[dict] = []

    def add(name, ok, value, expected):
        checks.append({"name": name, "ok": bool(ok), "value": value, "expected": expected})

    if v is None:
        add("video stream", False, "none", "present")
        return checks
    add("resolution", (v["width"], v["height"]) == (meta["width"], meta["height"]),
        f"{v['width']}x{v['height']}", f"{meta['width']}x{meta['height']}")
    r = float(Fraction(v["r_frame_rate"]))
    avg = float(Fraction(v["avg_frame_rate"])) if v.get("avg_frame_rate", "0/0") != "0/0" else r
    add("frame rate", abs(r - fps) < 0.01, round(r, 3), fps)
    add("constant frame rate", abs(avg - r) < 0.01, round(avg, 3), round(r, 3))
    dur = float(info["format"].get("duration", v.get("duration", 0)))
    add("duration", abs(dur - duration) <= 1.0 / fps + 1e-6, round(dur, 3), duration)
    add("codec", v["codec_name"] == "h264", v["codec_name"], "h264")
    add("pixel format", v.get("pix_fmt") == "yuv420p", v.get("pix_fmt"), "yuv420p")

    if audio.get("out") or audio.get("music"):
        if a is None:
            add("audio stream", False, "none", "48 kHz stereo")
        else:
            add("audio format", a.get("sample_rate") == "48000" and a.get("channels") == 2,
                f"{a.get('sample_rate')} Hz, {a.get('channels')} ch", "48000 Hz, 2 ch")
            target, tp = audio.get("lufs", -14), audio.get("true_peak", -1)
            if events["lufs"] is not None:
                add("loudness", abs(events["lufs"] - target) <= 1.0, events["lufs"], f"{target} ±1 LUFS")
            if events["true_peak"] is not None:
                add("true peak", events["true_peak"] <= tp + 0.1, events["true_peak"], f"≤ {tp} dBTP")

    allow = tl.get("qc_allow", [])
    for kind in ("black", "freeze", "silence"):
        bad = [(s, e) for s, e in events[kind] if not allowed(kind, s, e, allow, duration)]
        add(f"no unplanned {kind}", not bad,
            [f"{s:.2f}-{'end' if e is None else f'{e:.2f}'}s" for s, e in bad], "none outside qc_allow")
    return checks


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("timeline")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    video, tl = Path(args.video), json.loads(Path(args.timeline).read_text(encoding="utf-8"))
    info = probe(video)
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    events = parse_events(analyze(video, has_audio))
    checks = evaluate(info, events, tl)
    failed = [c for c in checks if not c["ok"]]
    report = {"video": str(video), "pass": not failed, "checks": checks, "events": events}
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    for c in failed:
        print(f"FAIL {c['name']}: {c['value']} (expected {c['expected']})")
    print(f"{'PASS' if not failed else 'FAIL'} {len(checks) - len(failed)}/{len(checks)} checks" + (f" -> {args.out}" if args.out else ""))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
