#!/usr/bin/env python3
"""Recorded sound effects from Freesound, chosen by what people who heard them left behind. Needs ffmpeg.

    python3 lib/sfx.py search "<English query>" [--license cc0|by|any] [--max-dur 2] [--min-dur 0] [-n 8] [--urls]
        relevance pages re-ranked by downloads; prints  key  title  duration  ↓downloads ★rating(votes)  license  user  description
    python3 lib/sfx.py get <slug>/audio/sfx fs:<id>... [--licenses <slug>/licenses.json] [--allow-nc]
        downloads the HQ previews in parallel, converts them to 48 kHz 24-bit WAV, and logs each in licenses.json
    python3 lib/sfx.py measure <file>...
        one line per file: length, where the transient sits, peak, how long it rings, and where the energy is

You can't hear these clips, so rank on evidence: downloads first, the number of ratings over their average
(★4.4(380) beats ★4.9(6)), and the uploader's description of the source and recorder. Then measure before
trusting a hit: a popular "thud" can be a 3 s cinematic rumble.

Needs a free Freesound API key (https://freesound.org/apiv2/apply), read from FREESOUND_API_KEY or from
video/.freesound-key (gitignored; confirm with `git check-ignore -v`). The key is sent in a header, never printed.
Previews (~128 kbps mp3) are enough for SFX under a music bed; originals need OAuth2.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from array import array
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audio import RATE, read_wav_mono, transient_time  # noqa: E402

API = "https://freesound.org/apiv2/search/text/"
VIDEO_DIR = Path(__file__).resolve().parent.parent  # lib/ sits in video/
KEY_FILE = VIDEO_DIR / ".freesound-key"
INDEX = VIDEO_DIR / ".sfx-index.json"  # search results, so `get` knows the title, author, license and url
FIELDS = "id,name,duration,num_downloads,avg_rating,num_ratings,license,username,description,previews"
LICENSE_FILTER = {"cc0": 'license:"Creative Commons 0"',
                  "by": 'license:("Attribution" OR "Creative Commons 0")', "any": ""}


def commercial_ok(lic: str) -> bool:
    """CC0 and CC BY are; BY-NC and Sampling+ are not."""
    return lic == "CC0" or (lic.startswith("CC-BY") and "NC" not in lic and "ND" not in lic)


# ---------- search ----------

def license_short(url: str) -> str:
    """Freesound returns license URLs; turn one into CC0, CC-BY-4.0, CC-BY-NC-3.0 or Sampling+."""
    u = url.lower()
    version = (re.search(r"/(\d\.\d)/?$", u) or [None, ""])[1]
    if "publicdomain/zero" in u:
        return "CC0"
    if "sampling+" in u:
        return "Sampling+"
    m = re.search(r"/licenses/([a-z-]+)/", u)
    if m:
        return "CC-" + m[1].upper() + (f"-{version}" if version else "")
    return url or "?"


def filter_string(license: str, min_dur: float | None, max_dur: float | None) -> str:
    parts = [LICENSE_FILTER[license]] if LICENSE_FILTER[license] else []
    if min_dur is not None or max_dur is not None:
        parts.append(f"duration:[{min_dur if min_dur is not None else 0} TO {max_dur if max_dur is not None else '*'}]")
    return " ".join(parts)


def parse_results(payload: dict) -> list[dict]:
    rows = []
    for s in payload.get("results", []):
        desc = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s.get("description") or "")).split())
        rows.append({
            "key": f"fs:{s['id']}", "id": s["id"], "title": s.get("name", ""), "duration": float(s.get("duration") or 0),
            "downloads": int(s.get("num_downloads") or 0), "rating": float(s.get("avg_rating") or 0),
            "votes": int(s.get("num_ratings") or 0), "license": license_short(s.get("license", "")),
            "author": s.get("username", "?"), "desc": desc[:100],
            "preview": (s.get("previews") or {}).get("preview-hq-mp3", ""),
            "page": f"https://freesound.org/s/{s['id']}/",
        })
    return rows


def rank(rows: list[dict]) -> list[dict]:
    """Downloads first, then how many people rated it. Server-side download sorting lets globally popular
    sounds win on a loose tag match, so this re-ranks relevance results instead."""
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: (-r["downloads"], -r["votes"])):
        if r["key"] not in seen:
            seen.add(r["key"])
            out.append(r)
    return out


def format_row(r: dict, urls: bool = False) -> str:
    stats = f"↓{r['downloads']} ★{r['rating']:.1f}({r['votes']})" if r["votes"] else f"↓{r['downloads']} ★-"
    cols = [r["key"], r["title"], f"{r['duration']:.2f}s", stats, r["license"], r["author"], r["desc"]]
    return "\t".join(cols + ([r["preview"]] if urls else []))


def api_key() -> str:
    key = os.environ.get("FREESOUND_API_KEY", "").strip()
    if not key and KEY_FILE.is_file():
        key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit("no Freesound key: set FREESOUND_API_KEY or put it in video/.freesound-key "
                         "(free at https://freesound.org/apiv2/apply). Without one, use audio.py sfx.")
    return key


def fetch(url: str, key: str | None = None, timeout: float = 60, tries: int = 3) -> bytes:
    headers = {"User-Agent": "video-director-sfx"}
    if key:
        headers["Authorization"] = f"Token {key}"
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise SystemExit("Freesound rejected the API key (HTTP %d)" % e.code)
            if n == tries - 1 or e.code not in (429, 500, 502, 503, 504):
                raise
        except OSError:
            if n == tries - 1:
                raise
        time.sleep(2 * (n + 1))
    raise OSError("unreachable")


def load_index() -> dict:
    try:
        return json.loads(INDEX.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_index(rows: list[dict]) -> None:
    idx = load_index()
    idx.update({r["key"]: r for r in rows})
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")


def search(args) -> int:
    key = api_key()
    base = {"query": args.query, "fields": FIELDS, "page_size": 50, "sort": "score"}
    flt = filter_string(args.license, args.min_dur, args.max_dur)
    if flt:
        base["filter"] = flt

    def page(n):
        try:
            return json.loads(fetch(API + "?" + urllib.parse.urlencode({**base, "page": n}), key))
        except urllib.error.HTTPError as e:
            if e.code == 404:  # past the last page
                return {}
            raise

    with ThreadPoolExecutor(args.pages) as ex:
        rows = rank([r for p in ex.map(page, range(1, args.pages + 1)) for r in parse_results(p)])
    save_index(rows)
    for r in rows[:args.n]:
        print(format_row(r, args.urls))
    if not rows:
        print("(none) try a plainer noun, drop the duration filter, or --license any")
    return 0


# ---------- get ----------

def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def license_entry(row: dict, path: str) -> dict:
    lic = row["license"]
    credit = None if lic == "CC0" else f"\"{row['title']}\" by {row['author']} ({row['page']}), {lic}"
    return {"path": path, "source": row["page"], "license": lic, "attribution": credit,
            "note": "Freesound HQ preview, converted to WAV"}


def log_licenses(path: Path, entries: list[dict]) -> None:
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        current = []
    by_path = {e.get("path"): e for e in current}
    for e in entries:
        by_path[e["path"]] = e
    path.write_text(json.dumps(list(by_path.values()), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def to_wav(src: Path, dst: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ar", str(RATE), "-c:a", "pcm_s24le",
                    str(dst)], check=True)


def get(args) -> int:
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    lic_path = Path(args.licenses) if args.licenses else (
        out.parent.parent / "licenses.json" if out.parts[-2:] == ("audio", "sfx") else out / "licenses.json")
    idx, key = load_index(), api_key()

    def one(k: str):
        r = idx.get(k)
        if not r:
            return k, None, "unknown key: search for it first"
        if not args.allow_nc and not commercial_ok(r["license"]):
            return k, None, f"{r['license']} is not for commercial work (pass --allow-nc if this piece is non-commercial)"
        dst = out / f"fs{r['id']}-{slug(r['title']) or 'sfx'}.wav"
        if not dst.exists():
            with tempfile.TemporaryDirectory() as tmp:
                mp3 = Path(tmp) / "preview.mp3"
                mp3.write_bytes(fetch(r["preview"], key, timeout=300))
                to_wav(mp3, dst)
        return k, dst, r

    def safe(k: str):
        try:
            return one(k)
        except (OSError, subprocess.CalledProcessError) as e:  # one bad file shouldn't sink the batch
            return k, None, repr(e)

    entries, failed = [], 0
    # Freesound caps each connection at roughly 80 KB/s, so parallel downloads are the only speed lever.
    with ThreadPoolExecutor(6) as ex:
        for k, dst, info in ex.map(safe, args.keys):
            if dst is None:
                failed += 1
                print(f"FAIL {k}: {info}")
                continue
            rel = os.path.relpath(dst, lic_path.parent)
            entries.append(license_entry(info, rel))
            print(f"{rel}\t{info['license']}" + (f"\tcredit: {entries[-1]['attribution']}" if entries[-1]["attribution"] else ""))
    if entries:
        log_licenses(lic_path, entries)
        print(f"logged {len(entries)} in {lic_path}")
    return 1 if failed else 0


# ---------- measure ----------

def _band_split(x: array, rate: int) -> tuple[float, float, float]:
    """Share of energy below 250 Hz, 250 Hz-4 kHz and above 4 kHz, using two one-pole low-passes."""
    k_lo, k_hi = (1 - math.exp(-2 * math.pi * f / rate) for f in (250.0, 4000.0))
    lo = hi_lp = 0.0
    e = [0.0, 0.0, 0.0]
    for s in x:
        lo += k_lo * (s - lo)
        hi_lp += k_hi * (s - hi_lp)
        e[0] += lo * lo
        e[1] += (hi_lp - lo) ** 2
        e[2] += (s - hi_lp) ** 2
    total = sum(e) or 1.0
    return e[0] / total, e[1] / total, e[2] / total


def measure(samples: array, rate: int) -> dict:
    """Facts a listener would notice first, from the samples alone."""
    n = len(samples)
    peak = max((abs(x) for x in samples), default=0.0)
    if n == 0 or peak == 0:
        return {"dur": n / rate if rate else 0.0, "silent": True}
    win = max(1, rate // 100)  # 10 ms RMS windows
    env = [math.sqrt(sum(x * x for x in samples[i:i + win]) / len(samples[i:i + win])) for i in range(0, n, win)]
    top = max(env)
    loud = [i for i, v in enumerate(env) if v >= top * 0.01]  # within 40 dB of the loudest window
    peak_at = env.index(top)
    head = transient_time(samples, rate)
    ring = (loud[-1] + 1 - peak_at) * win / rate
    low, mid, high = _band_split(samples[:rate * 10], rate)
    return {"dur": n / rate, "transient": head, "peak_db": 20 * math.log10(peak), "ring": max(0.0, ring),
            "low": low, "mid": mid, "high": high, "silent": False}


def describe(m: dict) -> str:
    if m.get("silent"):
        return f"{m['dur']:.2f}s silent"
    body = max(("low", "mid", "high"), key=lambda b: m[b])
    notes = []
    if m["transient"] > 0.15:
        notes.append("late transient: the mixer aligns it, but check the lead-in")
    if m["ring"] > 1.5:
        notes.append("long ring: trim or fade it if the cue is a tap")
    if m["peak_db"] > -0.3:
        notes.append("may be clipped")
    return (f"{m['dur']:.2f}s  transient {m['transient']:.3f}s  peak {m['peak_db']:.1f} dBFS  rings {m['ring']:.2f}s  "
            f"energy low/mid/high {m['low']:.0%}/{m['mid']:.0%}/{m['high']:.0%} ({body})"
            + (f"  [{'; '.join(notes)}]" if notes else ""))


def read_any(path: Path) -> tuple[array, int]:
    if path.suffix.lower() == ".wav":
        try:
            return read_wav_mono(path)
        except (ValueError, OSError):
            pass  # float or odd WAVs go through ffmpeg
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "x.wav"
        to_wav(path, wav)
        return read_wav_mono(wav)


def measure_cmd(args) -> int:
    for f in args.files:
        samples, rate = read_any(Path(f))
        print(f"{f}\t{describe(measure(samples, rate))}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--license", choices=LICENSE_FILTER, default="by", help="by (default) allows CC0 and CC BY")
    s.add_argument("--min-dur", type=float)
    s.add_argument("--max-dur", type=float)
    s.add_argument("-n", type=int, default=8)
    s.add_argument("--pages", type=int, default=2, help="relevance pages of 50 to re-rank by downloads")
    s.add_argument("--urls", action="store_true", help="add preview links for the user to audition")
    g = sub.add_parser("get")
    g.add_argument("out_dir")
    g.add_argument("keys", nargs="+")
    g.add_argument("--licenses", help="licenses.json to log into (default: the slug's, from <slug>/audio/sfx)")
    g.add_argument("--allow-nc", action="store_true")
    m = sub.add_parser("measure")
    m.add_argument("files", nargs="+")
    args = ap.parse_args(argv)
    try:
        return {"search": search, "get": get, "measure": measure_cmd}[args.cmd](args)
    except (OSError, urllib.error.URLError) as e:
        raise SystemExit(f"network error: {getattr(e, 'reason', e)}. Freesound can be slow or blocked on some "
                         "networks; retry, set https_proxy, or fall back to audio.py sfx.")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
