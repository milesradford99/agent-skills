#!/usr/bin/env python3
"""Turn a video into images a model can review. Needs ffmpeg.

    python3 lib/frames.py sheet  video.mp4 out_dir [--fps 2] [--cols 6] [--rows 5] [--width 320]
    python3 lib/frames.py burst  video.mp4 6.5 out.png [--window 0.5] [--width 384]
    python3 lib/frames.py still  video.mp4 6.5 out.png
    python3 lib/frames.py review video.mp4 timeline.json out_dir      everything the reviewer gets

Contact sheets carry burned-in timecodes when ffmpeg has drawtext; otherwise each sheet gets an
index file listing the time of every cell.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

LABEL = "drawtext=text='%{pts\\:hms}':x=6:y=6:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=4"


def ff(args: list[str]) -> bool:
    return subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args]).returncode == 0


def duration_of(video: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def sheet(video: Path, out_dir: Path, fps: float = 2, cols: int = 6, rows: int = 5, width: int = 320) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(out_dir / "sheet-%02d.png")
    base = f"fps={fps},scale={width}:-2"
    tile = f"tile={cols}x{rows}:padding=4:margin=4"
    if not ff(["-i", str(video), "-vf", f"{base},{LABEL},{tile}", "-fps_mode", "vfr", pattern]):
        ff(["-i", str(video), "-vf", f"{base},{tile}", "-fps_mode", "vfr", pattern])
        per = cols * rows
        n = math.ceil(duration_of(video) * fps)
        lines = [f"sheet-{i // per + 1:02d}.png row {(i % per) // cols + 1} col {i % cols + 1}: {i / fps:.2f}s" for i in range(n)]
        (out_dir / "sheet-index.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sorted(out_dir.glob("sheet-*.png"))


def burst(video: Path, t: float, out: Path, window: float = 0.5, width: int = 384) -> bool:
    """Every native frame in [t - window/2, t + window/2), tiled, for judging motion around a moment.
    Timestamps are kept from the source (-copyts) so the labels are the video's real timecodes."""
    out.parent.mkdir(parents=True, exist_ok=True)
    start, end = max(0.0, t - window / 2), t + window / 2
    seek = max(0.0, start - 1.0)
    pick = f"select='gte(t\\,{start:.4f})*lt(t\\,{end:.4f})',scale={width}:-2"
    tile = "tile=5x4:padding=4:margin=4"
    head = ["-ss", f"{seek:.3f}", "-copyts", "-i", str(video)]
    return (ff([*head, "-vf", f"{pick},{LABEL},{tile}", "-frames:v", "1", str(out)])
            or ff([*head, "-vf", f"{pick},{tile}", "-frames:v", "1", str(out)]))


def still(video: Path, t: float, out: Path) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    return ff(["-i", str(video), "-ss", f"{t:.3f}", "-frames:v", "1", str(out)])


def review_pack(video: Path, tl: dict, out_dir: Path) -> dict:
    """Contact sheets, bursts around every cue and shot change, full-res stills at key cues, and audio pictures."""
    duration = tl["meta"]["duration"]
    pack = {"sheets": [str(p) for p in sheet(video, out_dir / "sheets")], "bursts": [], "stills": [], "audio": []}
    moments = {round(c["t"], 2): c["id"] for c in tl.get("cues", [])}
    for s in tl.get("shots", [])[1:]:
        moments.setdefault(round(s["start"], 2), f"cut-{s['id']}")
    for t, name in sorted(moments.items()):
        p = out_dir / "bursts" / f"{t:06.2f}-{name}.png"
        if burst(video, t, p):
            pack["bursts"].append(str(p))
    key = [c for c in tl.get("cues", []) if c.get("kind") in ("hook", "signature", "title", "end")]
    times = sorted({round(c["t"], 2) for c in key} | {round(max(0.0, duration - 0.5), 2)})
    for t in times:
        p = out_dir / "stills" / f"{t:06.2f}.png"
        if still(video, t, p):
            pack["stills"].append(str(p))
    wave = out_dir / "audio" / "waveform.png"
    spec = out_dir / "audio" / "spectrogram.png"
    wave.parent.mkdir(parents=True, exist_ok=True)
    if ff(["-i", str(video), "-filter_complex", "showwavespic=s=1600x240:split_channels=1", "-frames:v", "1", str(wave)]):
        pack["audio"].append(str(wave))
    if ff(["-i", str(video), "-lavfi", "showspectrumpic=s=1600x480:legend=1", str(spec)]):
        pack["audio"].append(str(spec))
    (out_dir / "pack.json").write_text(json.dumps(pack, indent=2), encoding="utf-8")
    return pack


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("video")
    s.add_argument("out_dir")
    s.add_argument("--fps", type=float, default=2)
    s.add_argument("--cols", type=int, default=6)
    s.add_argument("--rows", type=int, default=5)
    s.add_argument("--width", type=int, default=320)
    b = sub.add_parser("burst")
    b.add_argument("video")
    b.add_argument("t", type=float)
    b.add_argument("out")
    b.add_argument("--window", type=float, default=0.5)
    b.add_argument("--width", type=int, default=384)
    st = sub.add_parser("still")
    st.add_argument("video")
    st.add_argument("t", type=float)
    st.add_argument("out")
    r = sub.add_parser("review")
    r.add_argument("video")
    r.add_argument("timeline")
    r.add_argument("out_dir")
    args = ap.parse_args(argv)

    video = Path(args.video)
    if args.cmd == "sheet":
        for p in sheet(video, Path(args.out_dir), args.fps, args.cols, args.rows, args.width):
            print(p)
    elif args.cmd == "burst":
        return 0 if burst(video, args.t, Path(args.out), args.window, args.width) else 1
    elif args.cmd == "still":
        return 0 if still(video, args.t, Path(args.out)) else 1
    else:
        tl = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
        pack = review_pack(video, tl, Path(args.out_dir))
        print(f"{len(pack['sheets'])} sheets, {len(pack['bursts'])} bursts, {len(pack['stills'])} stills, "
              f"{len(pack['audio'])} audio images -> {Path(args.out_dir) / 'pack.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
