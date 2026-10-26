#!/usr/bin/env python3
"""Compose an original background score that follows the timeline's cues. Needs numpy.

    python3 lib/music.py <slug>/timeline.json [--out audio/music.wav] [--mood warm] [--seed 1]

Reads meta.duration, audio.bpm (default 90), audio.mood (warm, calm, bright, tense) and audio.sections.
Without sections, an arc is derived from the cues: soft from the hook, building toward the signature cue,
one bar of near-silence before it, full on it, then resolving and ringing out at the end.

    "sections": [{ "start": 0, "end": 12, "energy": 1 }, ...]     energy 0 (rest) .. 3 (full)

The score is a pad, a soft piano-like arpeggio, sub bass and light percussion, with a synthetic room.
It's a dependable bed, not a film score: say so, and prefer the user's own licensed track when they have one.
Writes 48 kHz stereo 24-bit WAV and sets nothing else; point audio.music at it and run audio.py mix.
"""

from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path

try:
    import numpy as np
except ImportError:  # pragma: no cover - reported to the agent, not a crash
    np = None

RATE = 48000

# Progressions as (semitones above the key's tonic, minor?) per chord, one chord per bar.
MOODS = {
    "warm": {"scale": "major", "prog": [(0, False), (9, True), (5, False), (7, False)]},      # I vi IV V
    "calm": {"scale": "major", "prog": [(9, True), (5, False), (0, False), (7, False)]},      # vi IV I V
    "bright": {"scale": "major", "prog": [(0, False), (7, False), (9, True), (5, False)]},    # I V vi IV
    "tense": {"scale": "minor", "prog": [(0, True), (8, False), (3, False), (10, False)]},    # i VI III VII
}
KEYS = {"C": 48, "D": 50, "E": 52, "F": 53, "G": 55, "A": 57}


def midi_hz(n: float) -> float:
    return 440.0 * 2 ** ((n - 69) / 12)


def derive_sections(tl: dict) -> list[dict]:
    dur = tl["meta"]["duration"]
    cues = {c.get("kind"): c["t"] for c in tl.get("cues", [])}
    bar = 4 * 60.0 / tl.get("audio", {}).get("bpm", 90)
    hook = min(cues.get("hook", 0.0), dur)
    sig = cues.get("signature", dur * 0.68)
    resolve = max(sig + 2 * bar, dur * 0.82)
    if resolve > dur - bar:  # short pieces: still settle for the last bar
        resolve = max(sig + bar / 2, dur - bar)
    out = [
        {"start": 0.0, "end": hook, "energy": 0},
        {"start": hook, "end": hook + (sig - hook) * 0.45, "energy": 1},
        {"start": hook + (sig - hook) * 0.45, "end": sig - bar, "energy": 2},
        {"start": sig - bar, "end": sig, "energy": 0},
        {"start": sig, "end": min(resolve, dur), "energy": 3},
        {"start": min(resolve, dur), "end": dur, "energy": 1},
    ]
    return [s for s in out if s["end"] - s["start"] > 1e-3]


def energy_at(sections: list[dict], t: float) -> int:
    for s in sections:
        if s["start"] <= t < s["end"]:
            return int(s["energy"])
    return 0


def _add(buf, start: float, sig) -> None:
    i = int(start * RATE)
    if i >= buf.shape[1] or i + len(sig) <= 0:
        return
    j = min(buf.shape[1], i + sig.shape[1])
    buf[:, i:j] += sig[:, : j - i]


def _env(n: int, attack: float, release: float) -> "np.ndarray":
    a, r = max(1, int(attack * RATE)), max(1, int(release * RATE))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, min(a, n))[: min(a, n)]
    if r < n:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def pad(freqs: list[float], dur: float, rnd) -> "np.ndarray":
    n = int(dur * RATE)
    t = np.arange(n) / RATE
    out = np.zeros((2, n))
    for f in freqs:
        for ch, det in ((0, 0.997), (1, 1.003)):
            for h in range(1, 7):
                ph = rnd.uniform(0, 2 * np.pi)
                out[ch] += np.sin(2 * np.pi * f * det * h * t + ph) / h ** 1.6
    return out * _env(n, min(1.2, dur / 3), min(1.5, dur / 3)) / (len(freqs) * 3)


def pluck(f: float, dur: float) -> "np.ndarray":
    n = int(dur * RATE)
    t = np.arange(n) / RATE
    s = sum(np.sin(2 * np.pi * f * h * t) * np.exp(-t * (2.2 + 1.8 * h)) / h ** 1.2 for h in range(1, 7))
    s *= _env(n, 0.004, 0.08)
    return np.vstack([s, s])


def bass(f: float, dur: float) -> "np.ndarray":
    n = int(dur * RATE)
    t = np.arange(n) / RATE
    s = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * _env(n, 0.01, 0.12)
    return np.vstack([s, s])


def kick() -> "np.ndarray":
    n = int(0.35 * RATE)
    t = np.arange(n) / RATE
    ph = 2 * np.pi * np.cumsum(45 + 75 * np.exp(-t * 30)) / RATE
    s = np.sin(ph) * np.exp(-t * 9)
    return np.vstack([s, s])


def hat(rnd) -> "np.ndarray":
    n = int(0.06 * RATE)
    noise = rnd.uniform(-1, 1, n)
    s = (noise - np.convolve(noise, np.ones(6) / 6, mode="same")) * np.exp(-np.arange(n) / RATE * 70)
    return np.vstack([s * 0.9, s])


def room(x: "np.ndarray", rnd, seconds: float = 1.8, wet: float = 0.22) -> "np.ndarray":
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    out = np.empty_like(x)
    size = 1 << int(np.ceil(np.log2(x.shape[1] + n)))
    for ch in range(2):
        ir = rnd.normal(0, 1, n) * np.exp(-t * 6.9 / seconds)
        ir[: int(0.012 * RATE)] = 0  # pre-delay
        ir /= np.sqrt(np.sum(ir ** 2))
        y = np.fft.irfft(np.fft.rfft(x[ch], size) * np.fft.rfft(ir, size), size)[: x.shape[1]]
        out[ch] = x[ch] * (1 - wet) + y * wet
    return out


def compose(tl: dict, mood: str = "warm", seed: int = 1) -> "np.ndarray":
    if np is None:
        raise SystemExit("music.py needs numpy (pip install numpy, or use a Python that has it)")
    audio = tl.get("audio", {})
    dur = float(tl["meta"]["duration"])
    bpm = float(audio.get("bpm", 90))
    mood = audio.get("mood", mood)
    spec = MOODS.get(mood, MOODS["warm"])
    tonic = KEYS.get(str(audio.get("key", "C")).upper(), 48)
    sections = audio.get("sections") or derive_sections(tl)
    rnd = np.random.default_rng(seed)
    beat = 60.0 / bpm
    bar = 4 * beat
    offset = float(audio.get("offset", 0.0))
    tail = 3.0
    buf = np.zeros((2, int((dur + tail) * RATE)))

    n_bars = int(np.ceil((dur - offset) / bar)) + 1
    for b in range(n_bars):
        t0 = offset + b * bar
        if t0 >= dur:
            break
        e = max(energy_at(sections, t0 + 0.01), energy_at(sections, t0 + bar * 0.5))
        root, minor = spec["prog"][b % len(spec["prog"])]
        r = tonic + root
        triad = [r, r + (3 if minor else 4), r + 7]
        last = t0 + bar >= dur - 1e-6
        length = (dur - t0 + tail) if last else bar + 0.6
        if e >= 1 or last:
            voicing = [midi_hz(n + 12) for n in triad] + [midi_hz(r)]
            _add(buf, t0, pad(voicing, length, rnd) * (0.55 if e <= 1 else 0.62))
        if e >= 1 and not last:
            pattern = [0, 2, 1, 2, 0, 2, 1, 2] if e >= 2 else [0, 1, 2, 1]
            step = bar / len(pattern)
            for k, idx in enumerate(pattern):
                note = triad[idx] + 24
                _add(buf, t0 + k * step, pluck(midi_hz(note), step * 3) * (0.16 if e == 1 else 0.2))
        if e >= 2 and not last:
            for k in (0, 2):
                _add(buf, t0 + k * beat, bass(midi_hz(r - 12), beat * 1.8) * 0.16)
        if e >= 3 and not last:
            for k in range(4):
                _add(buf, t0 + k * beat, kick() * 0.5)
                _add(buf, t0 + (k + 0.5) * beat, hat(rnd) * 0.06)
        if last:
            _add(buf, t0, bass(midi_hz(r - 12), min(length, 4.0)) * 0.25)

    buf = room(buf, rnd)
    buf = buf[:, : int(dur * RATE)]
    fade = int(min(2.0, dur / 4) * RATE)
    buf[:, -fade:] *= np.linspace(1, 0, fade) ** 1.5
    peak = np.max(np.abs(buf)) or 1.0
    return buf * (10 ** (-6 / 20) / peak)  # leave headroom; audio.py mix sets the level


def write_wav(path: Path, x: "np.ndarray") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ints = np.ascontiguousarray((np.clip(x.T, -1, 1) * 8388607).astype("<i4"))
    raw = ints.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(RATE)
        w.writeframes(raw)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("timeline")
    ap.add_argument("--out", default="audio/music.wav", help="relative to the project folder")
    ap.add_argument("--mood", default="warm", choices=sorted(MOODS))
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args(argv)
    path = Path(args.timeline)
    tl = json.loads(path.read_text(encoding="utf-8"))
    out = path.parent / args.out
    write_wav(out, compose(tl, args.mood, args.seed))
    print(f"{out} ({tl['meta']['duration']:g}s, {tl.get('audio', {}).get('mood', args.mood)}, "
          f"{tl.get('audio', {}).get('bpm', 90):g} bpm); set audio.music to \"{args.out}\" and run audio.py mix")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
