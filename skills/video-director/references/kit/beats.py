#!/usr/bin/env python3
"""Find a track's tempo, beat grid and big accents, so picture lands on what the music does. Needs ffmpeg and numpy.

    python3 lib/beats.py <track> --fps 30 [--out <slug>/audio/beats.json] [--accents 8] [--min-t 3] [--per-bar 4]

Works on any format ffmpeg reads, assumes one steady tempo, and writes:

    { "bpm": 78.0, "offset": 0.41, "downbeat": 1.95, "per_bar": 4, "duration": 134.2, "first_big": 17.1,
      "accents": [{ "t": 17.1, "frame": 513, "strength": 1.0 }, ...] }

Copy bpm and offset into audio.bpm and audio.offset so on_beat cues snap to the grid. An accent is a moment
the music gets suddenly bigger (a drop, an entry, a hit), which isn't the same as a beat; strength is relative
to the loudest one. first_big is the earliest strong accent after --min-t, usually where a title card belongs.
Give a cue "on_accent": true and timeline.py check holds it to the file.

For footage cut to a song with tempo changes, use Beat This! as pipeline.md says; this is the light option.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError:  # the tool says what's missing instead of tracing back
    np = None

RATE = 22050
HOP = 256
WINDOW = 1024
LOW_HZ = 200
FLUX_LEAD = WINDOW / 4 / RATE  # flux rises as an onset enters the window, ahead of the window's centre


def load(path: Path) -> "np.ndarray":
    run = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"],
                         capture_output=True, check=True)
    return np.frombuffer(run.stdout, dtype=np.float32).astype(np.float64)


def onset_envelope(x: "np.ndarray") -> tuple["np.ndarray", "np.ndarray"]:
    """Spectral flux, how much new energy arrives in each hop: across all bands, and below about 200 Hz."""
    x = np.pad(x, WINDOW // 2)
    count = max(1, (len(x) - WINDOW) // HOP + 1)
    window = np.hanning(WINDOW)
    env, low = np.zeros(count), np.zeros(count)
    bins = max(2, int(LOW_HZ * WINDOW / RATE))
    prev = None
    for start in range(0, count, 512):  # in blocks, so a long track doesn't need one huge array
        idx = np.arange(start, min(start + 512, count))
        frames = np.stack([x[i * HOP:i * HOP + WINDOW] for i in idx]) * window
        mag = np.log1p(100 * np.abs(np.fft.rfft(frames, axis=1)))
        step = np.diff(np.vstack([mag[0] if prev is None else prev, mag]), axis=0)
        rise = np.maximum(step, 0)
        env[idx], low[idx] = rise.sum(axis=1), rise[:, :bins].sum(axis=1)
        prev = mag[-1]
    return env, low


def tempo(env: "np.ndarray", low: float = 60.0, high: float = 180.0) -> float:
    """Autocorrelation for the tempo family, weighted toward moderate tempi to settle doubling and halving."""
    e = env - env.mean()
    spectrum = np.fft.rfft(e, 2 * len(e))
    ac = np.fft.irfft(spectrum * np.conj(spectrum))[:len(e)]
    hops_per_s = RATE / HOP
    lags = np.arange(max(2, int(hops_per_s * 60 / high)), min(len(ac) - 1, int(hops_per_s * 60 / low) + 1))
    if len(lags) == 0:
        return 120.0
    bpm = 60 * hops_per_s / lags
    weight = np.exp(-0.5 * (np.log2(bpm / 100.0) / 0.9) ** 2)
    return float(bpm[np.argmax(ac[lags] * weight)])


def comb(env: "np.ndarray", bpm: float, offsets: "np.ndarray") -> "np.ndarray":
    """Onset energy under a beat grid, one score per offset (in seconds)."""
    period = 60.0 / bpm
    count = int((len(env) * HOP / RATE) / period) + 1
    times = offsets[:, None] + period * np.arange(count)[None, :]
    idx = np.rint(times * RATE / HOP).astype(int)
    return np.where(idx < len(env), env[np.minimum(idx, len(env) - 1)], 0.0).sum(axis=1)


def fit_grid(env: "np.ndarray", guess: float) -> tuple[float, float]:
    """Refine the tempo so the grid doesn't drift over a long track, then find its phase."""
    best = (-1.0, guess, 0.0)
    for span, step in ((0.03, 0.002), (0.002, 0.0002)):
        for bpm in best[1] * np.arange(1 - span, 1 + span, step):
            offsets = np.arange(0, 60.0 / bpm, HOP / RATE)
            scores = comb(env, bpm, offsets)
            i = int(np.argmax(scores))
            if scores[i] > best[0]:
                best = (float(scores[i]), float(bpm), float(offsets[i]))
    return best[1], best[2]


def on_the_beat(low: "np.ndarray", bpm: float, offset: float) -> float:
    """Bright off-beats can win the comb; kicks and bass say which half of the beat is the beat."""
    half = 30.0 / bpm
    other = (offset + half) % (2 * half)
    scores = comb(low, bpm, np.array([offset, other]))
    return float(other if scores[1] > scores[0] * 1.1 else offset)


def downbeat(low: "np.ndarray", bpm: float, offset: float, per_bar: int) -> float:
    """The grid phase with the strongest low end; with even pulses the first beat stands."""
    period = 60.0 / bpm
    bars = bpm / per_bar
    scores = [comb(low, bars, np.array([offset + n * period]))[0] for n in range(per_bar)]
    return offset + int(np.argmax(np.round(scores, 6))) * period


def _precise(x: "np.ndarray", t: float, reach: float = 0.06) -> float:
    """Pull an accent to where the waveform itself first reaches half its local peak."""
    a, b = max(0, int((t - reach) * RATE)), min(len(x), int((t + reach) * RATE))
    seg = np.abs(x[a:b])
    if seg.size == 0 or seg.max() == 0:
        return t
    return (a + int(np.argmax(seg >= seg.max() * 0.5))) / RATE


def find_accents(x: "np.ndarray", env: "np.ndarray", count: int, spacing: float = 2.0) -> list[dict]:
    """Onsets where the level after is well above the level before, biggest first until `count`."""
    hops_per_s = RATE / HOP
    rms = np.sqrt(np.convolve(x * x, np.ones(HOP) / HOP, mode="same")[::HOP][:len(env)] + 1e-10)
    level = 20 * np.log10(rms)
    before, after = int(1.5 * hops_per_s), int(0.4 * hops_per_s)
    score = np.zeros(len(env))
    limit = min(len(level), len(env))
    for i in np.flatnonzero(env[:limit] > env.mean() + env.std()):
        pre = level[max(0, i - before):i]
        post = level[i:i + after]
        if pre.size and post.size:
            score[i] = max(0.0, post.mean() - pre.mean()) * env[i]
    order, picked = np.argsort(-score), []
    for i in order:
        if score[i] <= 0 or len(picked) == count:
            break
        if all(abs(int(i) - p) >= spacing * hops_per_s for p in picked):
            picked.append(int(i))
    top = max((score[i] for i in picked), default=1.0)
    out = [{"t": _precise(x, i / hops_per_s), "strength": round(float(score[i] / top), 3)} for i in picked]
    return sorted(out, key=lambda a: a["t"])


def analyze(x: "np.ndarray", fps: float, accents: int = 8, min_t: float = 3.0, per_bar: int = 4) -> dict:
    env, low = onset_envelope(x)
    bpm, offset = fit_grid(env, tempo(env))
    offset = on_the_beat(low, bpm, offset)
    offset = (offset + FLUX_LEAD) % (60.0 / bpm)
    found = find_accents(x, env, accents)
    for a in found:
        a["t"] = round(a["t"], 3)
        a["frame"] = round(a["t"] * fps)
    strong = [a for a in found if a["strength"] >= 0.35 and a["t"] >= min_t] or [a for a in found if a["t"] >= min_t]
    return {"bpm": round(bpm, 2), "offset": round(offset, 3), "downbeat": round(downbeat(low, bpm, offset, per_bar), 3),
            "per_bar": per_bar, "duration": round(len(x) / RATE, 3), "first_big": strong[0]["t"] if strong else None,
            "accents": found}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("track")
    ap.add_argument("--fps", type=float, required=True)
    ap.add_argument("--out")
    ap.add_argument("--accents", type=int, default=8)
    ap.add_argument("--min-t", type=float, default=3.0, help="ignore accents before this for first_big")
    ap.add_argument("--per-bar", type=int, default=4)
    args = ap.parse_args(argv)
    if np is None:
        print("beats.py needs numpy: pip install numpy", file=sys.stderr)
        return 1
    result = analyze(load(Path(args.track)), args.fps, args.accents, args.min_t, args.per_bar)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{result['bpm']} BPM, offset {result['offset']}s, {len(result['accents'])} accents, "
          f"first big at {result['first_big']}s" + (f" -> {args.out}" if args.out else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
