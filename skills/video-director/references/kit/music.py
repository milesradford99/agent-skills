#!/usr/bin/env python3
"""Compose an original background score that follows the timeline's cues. Needs numpy.

    python3 lib/music.py <slug>/timeline.json [--out audio/music.wav] [--mood warm] [--seed 1]

Reads meta.duration, audio.bpm (default 90), audio.mood (warm, calm, bright, tense) and audio.sections.
Without sections, an arc is derived from the cues: soft from the hook, building toward the signature cue,
one bar of near-silence before it, full on it, then resolving and ringing out at the end.

    "sections": [{ "start": 0, "end": 12, "energy": 1 }, ...]     energy 0 (rest) .. 3 (full)

The score is a pad, a soft piano-like arpeggio, sub bass and light percussion, with a synthetic room.
It's a dependable bed, not a film score: say so, and prefer the user's own licensed track when they have one.

When the content itself is musical or rhythmic (a lesson on rhythm, a groove per genre, a heartbeat), add
audio.grooves: windows where the soundtrack plays the content's own pattern instead of the bed.

    "grooves": [{ "start": 30, "end": 76, "groove": "rock", "bpm": 120 },
                { "start": 80, "end": 96, "lanes": { "kick": "x..x..x.", "hat": "xxxxxxxx" }, "per_beat": 2 }]

A window names a preset from GROOVES or gives its own lanes (one character per step: x hit, X accent,
. rest; | is ignored), plus optional bpm, per_beat (steps per beat), swing (0..0.5 of a step on off-steps),
key, gain_db, and bed (0..1, how much of the bed stays under it; default 0). The bar is as long as the
pattern, so 7 steps at per_beat 2 is a bar of 7/8. Every hit is written to audio/events.json
({t, end, groove, window, lane, step, bar, accent}), and the page draws its on-screen instrument from that file,
so picture and sound share one source.

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

# Textbook patterns, simplified to a few lanes; each is one bar. They're teaching approximations: say so on
# screen if a viewer could take one for the only way the genre is played.
GROOVES = {
    "heartbeat": {"bpm": 70, "per_beat": 4, "lanes": {"kick": "Xx.."}},
    "march": {"bpm": 112, "per_beat": 4, "lanes": {"kick": "X...x...", "snare": "x.xx..x.", "bass": "x...x...", "stab": "..x...x."}},
    "waltz": {"bpm": 90, "per_beat": 2, "lanes": {"kick": "X.....", "bass": "X.....", "stab": "..x.x."}},
    "rock": {"bpm": 120, "per_beat": 2, "lanes": {"kick": "X...x.x.", "snare": "..X...X.", "hat": "xxxxxxxx", "bass": "x.x.x.x."}},
    "disco": {"bpm": 120, "per_beat": 4, "lanes": {"kick": "x...x...x...x...", "clap": "....X.......X...",
                                                "hat": "x...x...x...x...", "ohat": "..x...x...x...x.", "bass": "x.x.x.x.x.x.x.x."}},
    "funk": {"bpm": 100, "per_beat": 4, "lanes": {"kick": "X..x..x...x..x..", "snare": "....X..x.x..X...",
                                               "hat": "xxxxxxxxxxxxxxxx", "bass": "x..x..x...x.x...", "stab": ".x....x..x....x."}},
    "trap": {"bpm": 140, "per_beat": 4, "lanes": {"kick": "x......x..x.....", "clap": "........X.......",
                                               "hat": "x.x.x.x.xxxxx.x.", "bass": "x......x..x....."}},
    "reggae": {"bpm": 76, "per_beat": 4, "lanes": {"kick": "........X.......", "rim": "........x.......",
                                                "hat": "x.x.x.x.x.x.x.x.", "stab": "..x...x...x...x.", "bass": "x.....x.x......."}},
    "shuffle": {"bpm": 96, "per_beat": 2, "swing": 0.33, "lanes": {"kick": "x...x...", "snare": "..X...X.", "hat": "xxxxxxxx", "bass": "x.x.x.x."}},
    "bossa": {"bpm": 130, "per_beat": 4, "lanes": {"kick": "x..xx..xx..xx..x", "rim": "x..x..x...x..x..",
                                                "hat": "xxxxxxxxxxxxxxxx", "bass": "x.....x.x.....x."}},
    "tresillo": {"bpm": 100, "per_beat": 2, "lanes": {"kick": "X..x..x.", "hat": "xxxxxxxx", "bass": "x..x..x."}},
    "dembow": {"bpm": 96, "per_beat": 4, "lanes": {"kick": "x...x...x...x...", "snare": "...x..x....x..x.",
                                                "hat": "x.x.x.x.x.x.x.x.", "bass": "x..x..x.x..x..x."}},
    "seven-eight": {"bpm": 120, "per_beat": 2, "lanes": {"kick": "X.x.x..", "snare": "..x.x..", "hat": "xxxxxxx", "bass": "x.x.x.."}},
}
LANES = ("kick", "snare", "clap", "rim", "hat", "ohat", "bass", "stab")


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


def snare(rnd) -> "np.ndarray":
    n = int(0.22 * RATE)
    t = np.arange(n) / RATE
    noise = rnd.uniform(-1, 1, n)
    s = noise * np.exp(-t * 22) * 0.7 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.6
    return np.vstack([s, s])


def clap(rnd) -> "np.ndarray":
    n = int(0.25 * RATE)
    t = np.arange(n) / RATE
    noise = rnd.uniform(-1, 1, n)
    noise = noise - np.convolve(noise, np.ones(4) / 4, mode="same")
    env = sum(np.exp(-np.clip(t - d, 0, None) * 140) * (t >= d) for d in (0, 0.011, 0.022)) + np.exp(-t * 18) * (t >= 0.03)
    s = noise * env * 0.6
    return np.vstack([s * 0.95, s])


def rim() -> "np.ndarray":
    n = int(0.05 * RATE)
    t = np.arange(n) / RATE
    s = (np.sin(2 * np.pi * 1700 * t) + 0.5 * np.sin(2 * np.pi * 820 * t)) * np.exp(-t * 90)
    return np.vstack([s, s])


def open_hat(rnd) -> "np.ndarray":
    n = int(0.3 * RATE)
    noise = rnd.uniform(-1, 1, n)
    s = (noise - np.convolve(noise, np.ones(6) / 6, mode="same")) * np.exp(-np.arange(n) / RATE * 11)
    return np.vstack([s, s * 0.9])


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


def _steps(pattern: str) -> str:
    return pattern.replace("|", "").replace(" ", "")


def resolve_grooves(tl: dict) -> list[dict]:
    """Expand audio.grooves into full windows (preset merged with overrides). Raises ValueError on bad input."""
    dur = float(tl["meta"]["duration"])
    default_bpm = float(tl.get("audio", {}).get("bpm", 90))
    out = []
    for i, g in enumerate(tl.get("audio", {}).get("grooves", [])):
        where = f"audio.grooves[{i}]"
        name = g.get("groove")
        if name is not None and name not in GROOVES:
            raise ValueError(f"{where}: unknown groove '{name}' (known: {', '.join(GROOVES)})")
        base = GROOVES.get(name, {})
        lanes = {k: _steps(v) for k, v in (g.get("lanes") or base.get("lanes") or {}).items()}
        if not lanes:
            raise ValueError(f"{where}: needs a groove name or lanes")
        for lane, pat in lanes.items():
            if lane not in LANES:
                raise ValueError(f"{where}: unknown lane '{lane}' (use {', '.join(LANES)})")
            if set(pat) - set("xX.-"):
                raise ValueError(f"{where}: lane '{lane}' may only use x, X, . or -")
        lengths = {len(p) for p in lanes.values()}
        if len(lengths) != 1 or 0 in lengths:
            raise ValueError(f"{where}: every lane needs the same, non-zero number of steps")
        start, end = float(g.get("start", 0)), float(g.get("end", dur))
        if not 0 <= start < end <= dur + 1e-9:
            raise ValueError(f"{where}: needs 0 <= start < end <= duration")
        swing = float(g.get("swing", base.get("swing", 0.0)))
        if not 0 <= swing <= 0.5:
            raise ValueError(f"{where}: swing must be 0..0.5")
        out.append({
            "start": start, "end": end, "name": name or f"custom-{i}", "lanes": lanes,
            "steps": lengths.pop(), "bpm": float(g.get("bpm", base.get("bpm", default_bpm))),
            "per_beat": int(g.get("per_beat", base.get("per_beat", 4))), "swing": swing,
            "key": g.get("key"), "gain_db": float(g.get("gain_db", 0.0)), "bed": float(g.get("bed", 0.0)),
        })
    out.sort(key=lambda w: w["start"])
    for a, b in zip(out, out[1:]):
        if b["start"] < a["end"] - 1e-9:
            raise ValueError(f"grooves '{a['name']}' and '{b['name']}' overlap")
    return out


def groove_events(tl: dict) -> list[dict]:
    """Every hit of every groove window, in time order: the one source for both the audio and the picture."""
    events = []
    for wi, w in enumerate(resolve_grooves(tl)):
        step = 60.0 / w["bpm"] / w["per_beat"]
        bar_len = step * w["steps"]
        bar = 0
        while w["start"] + bar * bar_len < w["end"] - 1e-9:
            t0 = w["start"] + bar * bar_len
            for k in range(w["steps"]):
                t = t0 + k * step + (w["swing"] * step if k % 2 else 0.0)
                if t >= w["end"] - 1e-9:
                    continue
                for lane, pat in w["lanes"].items():
                    if pat[k] in "xX":
                        events.append({"t": round(t, 6), "end": round(min(t + step, w["end"]), 6), "groove": w["name"],
                                       "window": wi, "lane": lane, "step": k, "bar": bar, "accent": pat[k] == "X"})
            bar += 1
    events.sort(key=lambda e: (e["t"], LANES.index(e["lane"])))
    return events


GAINS = {"kick": 0.5, "snare": 0.3, "clap": 0.28, "rim": 0.18, "hat": 0.07, "ohat": 0.08, "bass": 0.22, "stab": 0.1}


def render_grooves(tl: dict, spec: dict, tonic: int, rnd, length: int) -> "np.ndarray":
    buf = np.zeros((2, length))
    windows = resolve_grooves(tl)
    for e in groove_events(tl):
        w = windows[e["window"]]
        key = KEYS.get(str(w["key"]).upper(), tonic) if w["key"] else tonic
        bars_per_chord = max(1, round(4 * w["per_beat"] / w["steps"]))  # short bars (1 beat, 2/4) hold a chord longer
        root, minor = spec["prog"][(e["bar"] // bars_per_chord) % len(spec["prog"])]
        r = key + root
        dur = e["end"] - e["t"]
        lane = e["lane"]
        if lane == "kick":
            sig = kick()
        elif lane == "snare":
            sig = snare(rnd)
        elif lane == "clap":
            sig = clap(rnd)
        elif lane == "rim":
            sig = rim()
        elif lane == "hat":
            sig = hat(rnd)
        elif lane == "ohat":
            sig = open_hat(rnd)
        elif lane == "bass":
            sig = bass(midi_hz(r - 12), max(dur * 1.6, 0.12))
        else:
            sig = sum(pluck(midi_hz(n + 12), max(dur * 2, 0.15)) for n in (r, r + (3 if minor else 4), r + 7)) / 2
        g = GAINS[lane] * (1.35 if e["accent"] else 1.0) * 10 ** (w["gain_db"] / 20)
        _add(buf, e["t"], sig * g)
    return buf


def bed_mask(tl: dict, length: int) -> "np.ndarray":
    """1 where the bed plays, each window's `bed` level inside groove windows, with 60 ms ramps."""
    mask = np.ones(length)
    ramp = int(0.06 * RATE)
    for w in resolve_grooves(tl):
        i, j = int(w["start"] * RATE), min(length, int(w["end"] * RATE))
        mask[i:j] = w["bed"]
        for a, b, lo, hi in ((max(0, i - ramp), i, 1.0, w["bed"]), (j, min(length, j + ramp), w["bed"], 1.0)):
            if b > a:
                mask[a:b] = np.minimum(mask[a:b], np.linspace(lo, hi, b - a))
    return mask


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
    if audio.get("grooves"):
        buf *= bed_mask(tl, buf.shape[1])
        buf += room(render_grooves(tl, spec, tonic, rnd, buf.shape[1]), rnd, seconds=0.8, wet=0.1)
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
    ap.add_argument("--events", default="audio/events.json", help="where groove hits are written, relative to the project")
    args = ap.parse_args(argv)
    path = Path(args.timeline)
    tl = json.loads(path.read_text(encoding="utf-8"))
    out = path.parent / args.out
    try:
        events = groove_events(tl)
    except ValueError as e:
        print(f"music.py: {e}", file=sys.stderr)
        return 1
    write_wav(out, compose(tl, args.mood, args.seed))
    if events:
        ev = path.parent / args.events
        ev.parent.mkdir(parents=True, exist_ok=True)
        ev.write_text(json.dumps(events, separators=(",", ":")), encoding="utf-8")
        print(f"{ev} ({len(events)} hits); draw the on-screen instrument from it")
    print(f"{out} ({tl['meta']['duration']:g}s, {tl.get('audio', {}).get('mood', args.mood)}, "
          f"{tl.get('audio', {}).get('bpm', 90):g} bpm); set audio.music to \"{args.out}\" and run audio.py mix")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
