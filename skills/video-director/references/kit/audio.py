#!/usr/bin/env python3
"""Sound effects and the timeline mix. SFX synthesis is standard library only; mixing and mastering use ffmpeg.

    python3 lib/audio.py sfx whoosh <slug>/audio/sfx/whoosh.wav [--dur 0.8] [--seed 1] [--pitch 1.0]
        kinds: whoosh, riser, impact, click, subdrop
    python3 lib/audio.py mix <slug>/timeline.json          places every cue's sfx (transient on the cue),
                                                            the music bed and ducking, then masters to
                                                            audio.lufs / audio.true_peak into audio.out
    python3 lib/audio.py master in.wav out.wav [--lufs -14] [--tp -1]   two-pass loudnorm, 48 kHz

SFX are 48 kHz mono 24-bit WAV. Recipes are deliberately simple; layer and EQ them in the mix,
or replace them with recorded CC0 sounds (log those in licenses.json).
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import subprocess
import sys
import wave
from array import array
from pathlib import Path

RATE = 48000


# ---------- WAV io ----------

def write_wav(path: Path, samples: array, rate: int = RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = max((abs(x) for x in samples), default=0.0)
    gain = 0.89 / peak if peak > 0.89 else 1.0  # keep about -1 dBFS headroom
    out = bytearray()
    for x in samples:
        v = int(max(-1.0, min(1.0, x * gain)) * 8388607)
        out += (v & 0xFFFFFF).to_bytes(3, "little")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(3)
        w.setframerate(rate)
        w.writeframes(bytes(out))


def read_wav_mono(path: Path) -> tuple[array, int]:
    """Read a 16- or 24-bit PCM WAV, averaged to mono floats."""
    with wave.open(str(path), "rb") as w:
        ch, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if width not in (2, 3):
        raise ValueError(f"{path}: only 16- or 24-bit PCM is supported")
    scale = float(1 << (8 * width - 1))
    out = array("d")
    step = width * ch
    for i in range(0, len(raw) - step + 1, step):
        acc = 0.0
        for c in range(ch):
            b = raw[i + c * width:i + (c + 1) * width]
            acc += int.from_bytes(b, "little", signed=True) / scale
        out.append(acc / ch)
    return out, rate


def transient_time(samples: array, rate: int, threshold: float = 0.5) -> float:
    """Seconds from the file start to the first sample reaching threshold x peak.
    This is the moment that should land on the cue, not the file start."""
    peak = max((abs(x) for x in samples), default=0.0)
    if peak == 0:
        return 0.0
    level = peak * threshold
    for i, x in enumerate(samples):
        if abs(x) >= level:
            return i / rate
    return 0.0


# ---------- synthesis ----------

def _env(n: int, attack: float, release_curve: float = 3.0) -> list[float]:
    a = max(1, int(n * attack))
    return [i / a if i < a else ((n - i) / (n - a)) ** release_curve for i in range(n)]


def _onepole(x: list[float], cutoffs: list[float]) -> list[float]:
    """Time-varying one-pole low-pass; cutoffs in Hz per sample."""
    y, prev = [], 0.0
    for s, fc in zip(x, cutoffs):
        k = 1.0 - math.exp(-2.0 * math.pi * fc / RATE)
        prev += k * (s - prev)
        y.append(prev)
    return y


def sfx(kind: str, dur: float | None = None, seed: int = 1, pitch: float = 1.0) -> array:
    rnd = random.Random(seed)
    noise = lambda n: [rnd.uniform(-1, 1) for _ in range(n)]  # noqa: E731
    if kind == "whoosh":
        n = int(RATE * (dur or 0.8))
        # band sweeps up then down; a low-pass minus a lower low-pass gives a moving band
        sweep = [200 + 5000 * pitch * math.sin(math.pi * i / n) ** 2 for i in range(n)]
        src = noise(n)
        band = [a - b for a, b in zip(_onepole(src, sweep), _onepole(src, [f * 0.35 for f in sweep]))]
        env = [math.sin(math.pi * i / n) ** 1.5 for i in range(n)]
        return array("d", (b * e for b, e in zip(band, env)))
    if kind == "riser":
        n = int(RATE * (dur or 2.0))
        src = noise(n)
        cut = [300 + 9000 * pitch * (i / n) ** 2 for i in range(n)]
        filt = _onepole(src, cut)
        phase, out = 0.0, array("d")
        for i in range(n):
            u = i / n
            phase += 2 * math.pi * (110 * pitch * 2 ** (3 * u)) / RATE
            out.append((0.6 * filt[i] + 0.35 * math.sin(phase)) * u ** 2)
        return out
    if kind == "impact":
        n = int(RATE * (dur or 1.2))
        phase, out = 0.0, array("d")
        src = noise(n)
        for i in range(n):
            t = i / RATE
            f = (55 + 90 * math.exp(-t * 18)) * pitch
            phase += 2 * math.pi * f / RATE
            body = math.sin(phase) * math.exp(-t * 4.0)
            crack = src[i] * math.exp(-t * 60.0) * 0.7
            out.append(body + crack)
        return out
    if kind == "click":
        n = int(RATE * (dur or 0.06))
        src = noise(n)
        return array("d", (
            (math.sin(2 * math.pi * 3200 * pitch * i / RATE) * 0.6 + src[i] * 0.4) * math.exp(-i / RATE * 140)
            for i in range(n)))
    if kind == "subdrop":
        n = int(RATE * (dur or 1.5))
        phase, out = 0.0, array("d")
        for i in range(n):
            t = i / RATE
            phase += 2 * math.pi * (70 * pitch * math.exp(-t * 1.2) + 28) / RATE
            out.append(math.sin(phase) * min(1.0, t * 200) * math.exp(-t * 2.2))
        return out
    raise ValueError(f"unknown sfx kind '{kind}' (whoosh, riser, impact, click, subdrop)")


# ---------- mix ----------

def build_mix(tl: dict, project_dir: Path) -> list[str]:
    """Return the ffmpeg argument list that renders the unmastered mix next to audio.out (as *.raw.wav)."""
    audio = tl.get("audio", {})
    duration = tl["meta"]["duration"]
    final = project_dir / audio.get("out", "audio/mix.wav")
    out = final.with_name(final.stem + ".raw.wav")
    inputs: list[str] = []
    chains: list[str] = []
    labels: list[str] = []

    music = audio.get("music")
    if music:
        inputs += ["-i", str(project_dir / music)]
        duck = "".join(
            f",volume=enable='between(t,{d['start']},{d['end']})':volume={d.get('db', -8)}dB"
            for d in audio.get("duck", []))
        chains.append(f"[0:a]aresample={RATE},aformat=channel_layouts=stereo,"
                      f"volume={audio.get('music_gain_db', 0)}dB{duck}[m]")
        labels.append("[m]")

    for c in tl.get("cues", []):
        if not c.get("sfx"):
            continue
        path = project_dir / c["sfx"]
        lead = 0.0
        if path.suffix.lower() == ".wav" and path.is_file():
            samples, rate = read_wav_mono(path)
            lead = transient_time(samples, rate)
        start = max(0.0, c["t"] - lead)
        idx = len(inputs) // 2
        inputs += ["-i", str(path)]
        label = f"[s{idx}]"
        chains.append(f"[{idx}:a]aresample={RATE},aformat=channel_layouts=stereo,"
                      f"volume={c.get('gain_db', 0)}dB,adelay={round(start * 1000)}:all=1{label}")
        labels.append(label)

    if not labels:
        raise ValueError("nothing to mix: set audio.music or give cues an sfx")
    chains.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest,"
                  f"atrim=0:{duration},apad=whole_dur={duration}[out]")
    return ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(chains),
            "-map", "[out]", "-ar", str(RATE), "-c:a", "pcm_s24le", str(out)]


AAC_MARGIN_DB = 1.0  # AAC encoding adds inter-sample peaks; master this much below the delivery true peak


def _measure(src: Path, pre: str, target: str) -> dict:
    chain = f"{pre},loudnorm={target}:print_format=json" if pre else f"loudnorm={target}:print_format=json"
    run = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af", chain, "-f", "null", "-"],
                         capture_output=True, text=True, check=True)
    found = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", run.stderr)
    if not found:
        raise RuntimeError("loudnorm printed no measurement")
    return json.loads(found[-1])


def limiter_for(input_i: float, input_tp: float, lufs: float, tp: float) -> str:
    """A look-ahead limiter that leaves room for the loudness gain, or '' if none is needed.
    Without it, transient-heavy mixes (impacts, clicks) make loudnorm drop out of linear mode and overshoot."""
    gain = lufs - input_i
    if input_tp + gain <= tp:
        return ""
    ceiling_db = max(-24.0, tp - gain - 0.5)  # alimiter's limit can't go below -24 dB
    return f"alimiter=limit={10 ** (ceiling_db / 20):.4f}:level=false:attack=1:release=60:latency=1"


def master(src: Path, dst: Path, lufs: float = -14.0, tp: float = -1.0) -> dict:
    """Peak-limit if needed, then two-pass linear loudnorm; 48 kHz out. Returns the first measurement."""
    inner_tp = tp - AAC_MARGIN_DB
    target = f"I={lufs}:TP={inner_tp}:LRA=20"
    first = _measure(src, "", target)
    pre = limiter_for(float(first["input_i"]), float(first["input_tp"]), lufs, inner_tp)
    m = _measure(src, pre, target) if pre else first
    norm = (f"loudnorm={target}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    chain = f"{pre},{norm}" if pre else norm
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", chain, "-ar", str(RATE),
                    "-c:a", "pcm_s24le", str(dst)], check=True)
    return first


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sfx")
    s.add_argument("kind")
    s.add_argument("out")
    s.add_argument("--dur", type=float)
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--pitch", type=float, default=1.0)
    m = sub.add_parser("mix")
    m.add_argument("timeline")
    m.add_argument("--print", action="store_true", help="print the ffmpeg command instead of running it")
    ms = sub.add_parser("master")
    ms.add_argument("src")
    ms.add_argument("dst")
    ms.add_argument("--lufs", type=float, default=-14.0)
    ms.add_argument("--tp", type=float, default=-1.0)
    args = ap.parse_args(argv)

    if args.cmd == "sfx":
        write_wav(Path(args.out), sfx(args.kind, args.dur, args.seed, args.pitch))
        print(args.out)
    elif args.cmd == "mix":
        path = Path(args.timeline)
        tl = json.loads(path.read_text(encoding="utf-8"))
        cmd = build_mix(tl, path.parent)
        if args.print:
            print(" ".join(cmd))
            return 0
        raw = Path(cmd[-1])
        raw.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(cmd, check=True)
        audio = tl.get("audio", {})
        final = path.parent / audio.get("out", "audio/mix.wav")
        meas = master(raw, final, audio.get("lufs", -14.0), audio.get("true_peak", -1.0))
        print(f"{final} (raw mix was {meas['input_i']} LUFS, {meas['input_tp']} dBTP)")
    else:
        meas = master(Path(args.src), Path(args.dst), args.lufs, args.tp)
        print(f"{args.dst} (input was {meas['input_i']} LUFS, {meas['input_tp']} dBTP)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
