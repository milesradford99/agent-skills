#!/usr/bin/env python3
"""Turn a video into images a model can review. Needs ffmpeg.

    python3 lib/frames.py sheet  video.mp4 out_dir [--fps 2] [--cols 6] [--rows 5] [--width 320]
    python3 lib/frames.py burst  video.mp4 6.5 out.png [--window 0.5] [--width 384]
    python3 lib/frames.py still  video.mp4 6.5 out.png
    python3 lib/frames.py review video.mp4 timeline.json out_dir [--bursts 10] [--stills 6]
                                                      a budgeted pack for the reviewer
    python3 lib/frames.py pair   a.mp4 b.mp4 out_dir 12.5,60,114.7      A/B stills side by side, same timecodes
    python3 lib/frames.py tile   out.png img1.png img2.png ...           labelled 3x3 sheet of stills

Contact sheets carry burned-in timecodes when ffmpeg has drawtext; otherwise each sheet gets an
index file listing the time of every cell. The review pack is budgeted: about 120 sheet cells, at most
10 bursts and 6 stills (stills at 1280 px wide), so a 4-minute film costs about as much to review as a
30-second one. It prints the image count and an approximate token cost.
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


def still(video: Path, t: float, out: Path, width: int = 0) -> bool:
    """One frame at t; width 0 keeps full resolution (use it for typography checks)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    vf = ["-vf", f"scale={width}:-2"] if width else []
    return ff(["-i", str(video), "-ss", f"{t:.3f}", *vf, "-frames:v", "1", str(out)])


def tile(out: Path, images: list[Path], cols: int = 3, width: int = 640) -> bool:
    """Stills into one labelled sheet (label = file name), so they can be looked at as one image."""
    out.parent.mkdir(parents=True, exist_ok=True)
    height = width * 9 // 16  # every cell is boxed to 16:9, so vertical frames are letterboxed, not cropped
    args, chains = [], []
    for k, p in enumerate(images):
        args += ["-i", str(p)]
        label = p.stem.replace(":", "\\:").replace("'", "")
        chains.append(f"[{k}]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                      f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,drawtext=text='{label}':x=8:y=8:fontsize=22:"
                      f"fontcolor=white:box=1:boxcolor=black@0.6[v{k}]")
    if len(images) == 1:
        chains[-1] = chains[-1][: chains[-1].rindex("[v0]")]
    else:
        lay = "|".join(f"{(k % cols) * width}_{(k // cols) * height}" for k in range(len(images)))
        chains.append("".join(f"[v{k}]" for k in range(len(images)))
                      + f"xstack=inputs={len(images)}:layout={lay}:fill=black")
    return ff([*args, "-filter_complex", ";".join(chains), "-frames:v", "1", str(out)])


def pair(a: Path, b: Path, out_dir: Path, times: list[float], width: int = 960) -> list[str]:
    """For blind A/B rounds: A and B side by side at the same timecodes, one image per moment."""
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for t in times:
        out = out_dir / f"{t:06.2f}.png"
        graph = f"[0:v]scale={width}:-2[a];[1:v]scale={width}:-2[b];[a][b]hstack=inputs=2"
        if ff(["-ss", f"{t:.3f}", "-i", str(a), "-ss", f"{t:.3f}", "-i", str(b), "-filter_complex", graph,
               "-frames:v", "1", str(out)]):
            made.append(str(out))
    return made


KEY_KINDS = ("hook", "signature", "title", "end")


def sheet_fps(duration: float, max_cells: int = 120) -> float:
    """Sampling rate for contact sheets: 2 fps for short pieces, fewer for long ones, in 0.25 steps."""
    return max(0.25, min(2.0, math.floor(max_cells / max(duration, 1e-6) * 4) / 4))


def spread(items: list, n: int) -> list:
    if len(items) <= n:
        return items
    return [items[round(i * (len(items) - 1) / (n - 1))] for i in range(n)] if n > 1 else items[:1]


def pick_moments(tl: dict, max_bursts: int = 10) -> list[tuple[float, str]]:
    """Key cues first, then shot changes, then other cues, spread evenly across the piece."""
    cues = tl.get("cues", [])
    key = [(round(c["t"], 2), c["id"]) for c in cues if c.get("kind") in KEY_KINDS]
    cuts = [(round(s["start"], 2), f"cut-{s['id']}") for s in tl.get("shots", [])[1:]]
    rest = [(round(c["t"], 2), c["id"]) for c in cues if c.get("kind") not in KEY_KINDS]
    chosen = dict(spread(sorted(key), max_bursts))
    for group in (cuts, rest):
        room = max_bursts - len(chosen)
        if room <= 0:
            break
        for t, name in spread(sorted(x for x in group if x[0] not in chosen), room):
            chosen.setdefault(t, name)
    return sorted(chosen.items())


def image_tokens(path: Path) -> int:
    """Approximate vision tokens for a PNG (width x height / 750), read from its header."""
    with open(path, "rb") as f:
        head = f.read(24)
    w, h = int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
    return w * h // 750


def review_pack(video: Path, tl: dict, out_dir: Path, max_bursts: int = 10, max_stills: int = 6,
                still_width: int = 1280) -> dict:
    """A budgeted pack: contact sheets, bursts at the moments that matter, a few stills, audio pictures."""
    duration = tl["meta"]["duration"]
    fps = sheet_fps(duration)
    pack = {"sheet_fps": fps, "sheets": [str(p) for p in sheet(video, out_dir / "sheets", fps=fps)],
            "bursts": [], "stills": [], "audio": []}
    for t, name in pick_moments(tl, max_bursts):
        p = out_dir / "bursts" / f"{t:06.2f}-{name}.png"
        if burst(video, t, p):
            pack["bursts"].append(str(p))
    key = sorted({round(c["t"], 2) for c in tl.get("cues", []) if c.get("kind") in KEY_KINDS})
    times = spread(key, max_stills - 1) + [round(max(0.0, duration - 0.5), 2)]
    for t in sorted(set(times)):
        p = out_dir / "stills" / f"{t:06.2f}.png"
        if still(video, t, p, still_width):
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
    r.add_argument("--bursts", type=int, default=10)
    r.add_argument("--stills", type=int, default=6)
    pr = sub.add_parser("pair")
    pr.add_argument("a")
    pr.add_argument("b")
    pr.add_argument("out_dir")
    pr.add_argument("times")
    tl_ = sub.add_parser("tile")
    tl_.add_argument("out")
    tl_.add_argument("images", nargs="+")
    args = ap.parse_args(argv)

    if args.cmd == "tile":
        imgs = [Path(p) for p in args.images]
        for n in range(0, len(imgs), 9):
            out = Path(args.out) if len(imgs) <= 9 else Path(args.out).with_name(f"{Path(args.out).stem}-{n // 9 + 1}.png")
            if not tile(out, imgs[n:n + 9]):
                return 1
            print(out)
        return 0
    if args.cmd == "pair":
        for p in pair(Path(args.a), Path(args.b), Path(args.out_dir), [float(x) for x in args.times.split(",")]):
            print(p)
        return 0

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
        pack = review_pack(video, tl, Path(args.out_dir), args.bursts, args.stills)
        images = [Path(p) for k in ("sheets", "bursts", "stills", "audio") for p in pack[k]]
        tokens = sum(image_tokens(p) for p in images)
        print(f"{len(pack['sheets'])} sheets ({pack['sheet_fps']:g} fps), {len(pack['bursts'])} bursts, "
              f"{len(pack['stills'])} stills, {len(pack['audio'])} audio images; {len(images)} images, "
              f"~{tokens // 1000}k tokens -> {Path(args.out_dir) / 'pack.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
