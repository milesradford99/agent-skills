"""Tests for the video-director kit's Python tools. Run with: python3 -m unittest discover -s tests"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "skills" / "video-director" / "references" / "kit"
sys.path.insert(0, str(KIT))

import audio  # noqa: E402
import qc  # noqa: E402
import timeline  # noqa: E402

STARTER = json.loads((KIT / "starter" / "timeline.json").read_text(encoding="utf-8"))


def tl(**overrides):
    base = {
        "meta": {"width": 1920, "height": 1080, "fps": 30, "duration": 10.0, "seed": "s"},
        "audio": {"bpm": 120, "offset": 0.0},
        "shots": [{"id": "a", "start": 0, "end": 5}, {"id": "b", "start": 5, "end": 10}],
        "cues": [{"id": "hook", "t": 0.5, "kind": "hook"}],
    }
    base.update(overrides)
    return base


class TimelineTest(unittest.TestCase):
    def test_starter_is_valid(self):
        errors, warnings = timeline.check(STARTER, KIT / "starter")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_onetake_starter_is_valid_without_shot_modules(self):
        spec = json.loads((KIT / "starter-onetake" / "timeline.json").read_text(encoding="utf-8"))
        self.assertEqual(timeline.check(spec, KIT / "starter-onetake"), ([], []))

    def test_missing_shot_module_fails_when_using_the_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "shots").mkdir()
            errors, _ = timeline.check(tl(), Path(tmp))
            self.assertTrue(any("has no shots/a.js" in e for e in errors))

    def test_beat_grid_does_not_drift(self):
        grid = timeline.beat_grid(bpm=128, fps=30, count=129)
        # 128 beats at 128 BPM is exactly 60 s, frame 1800; accumulating rounded 14.06-frame beats would drift.
        self.assertEqual(grid[128]["frame"], 1800)
        self.assertTrue(grid[0]["downbeat"] and not grid[1]["downbeat"])

    def test_gap_between_shots_fails(self):
        errors, _ = timeline.check(tl(shots=[{"id": "a", "start": 0, "end": 4}, {"id": "b", "start": 5, "end": 10}]))
        self.assertTrue(any("gap" in e for e in errors))

    def test_overlapping_shots_are_allowed(self):
        errors, _ = timeline.check(tl(shots=[{"id": "a", "start": 0, "end": 5.5}, {"id": "b", "start": 5, "end": 10}]))
        self.assertEqual(errors, [])

    def test_off_beat_cue_fails(self):
        errors, _ = timeline.check(tl(cues=[{"id": "drop", "t": 1.3, "kind": "hit", "on_beat": True}]))
        self.assertTrue(any("off the beat grid" in e for e in errors))

    def test_unknown_cue_reference_fails(self):
        shots = [{"id": "a", "start": 0, "end": 10, "params": {"at": "cue:nope"}}]
        errors, _ = timeline.check(tl(shots=shots))
        self.assertTrue(any("unknown cue 'nope'" in e for e in errors))

    def test_pacing_warnings(self):
        cues = [{"id": "hook", "t": 1.2, "kind": "hook"}, {"id": "sig", "t": 9.6, "kind": "signature"}]
        _, warnings = timeline.check(tl(cues=cues))
        self.assertEqual(len(warnings), 3)  # late hook, signature outside 60-75%, short end hold


class AudioTest(unittest.TestCase):
    def test_sfx_kinds_render_and_peak_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            for kind in ("whoosh", "riser", "impact", "click", "subdrop"):
                path = Path(tmp) / f"{kind}.wav"
                audio.write_wav(path, audio.sfx(kind, dur=0.3))
                samples, rate = audio.read_wav_mono(path)
                self.assertEqual(rate, 48000)
                self.assertGreater(len(samples), 0)
                self.assertLessEqual(max(abs(x) for x in samples), 0.9)

    def test_sfx_is_seeded(self):
        self.assertEqual(audio.sfx("click", seed=3).tobytes(), audio.sfx("click", seed=3).tobytes())

    def test_transient_lands_on_cue(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            sfx = audio.sfx("riser", dur=1.0)  # loudest near its end, so the transient is late in the file
            audio.write_wav(project / "audio" / "sfx" / "riser.wav", sfx)
            lead = audio.transient_time(sfx, 48000)
            self.assertGreater(lead, 0.3)
            spec = tl(cues=[{"id": "hit", "t": 4.0, "sfx": "audio/sfx/riser.wav", "gain_db": -6}], audio={"out": "audio/mix.wav"})
            cmd = audio.build_mix(spec, project)
            graph = cmd[cmd.index("-filter_complex") + 1]
            samples, _ = audio.read_wav_mono(project / "audio" / "sfx" / "riser.wav")
            expected_ms = round((4.0 - audio.transient_time(samples, 48000)) * 1000)
            self.assertIn(f"adelay={expected_ms}:all=1", graph)
            self.assertTrue(cmd[-1].endswith("mix.raw.wav"))

    def test_limiter_only_when_gain_would_clip(self):
        self.assertEqual(audio.limiter_for(input_i=-16, input_tp=-8, lufs=-14, tp=-2), "")
        chain = audio.limiter_for(input_i=-22.9, input_tp=-6.6, lufs=-14, tp=-2)
        self.assertTrue(chain.startswith("alimiter=") and "latency=1" in chain)

    def test_music_ducking_in_graph(self):
        spec = tl(cues=[], audio={"music": "audio/music.wav", "duck": [{"start": 2, "end": 4, "db": -9}]})
        graph = audio.build_mix(spec, Path("/p"))
        self.assertIn("volume=enable='between(t,2,4)':volume=-9dB", graph[graph.index("-filter_complex") + 1])


FFMPEG_LOG = """
[blackdetect @ 0x1] black_start:0 black_end:0.4 black_duration:0.4
[freezedetect @ 0x2] lavfi.freezedetect.freeze_start: 3.2
[freezedetect @ 0x2] lavfi.freezedetect.freeze_duration: 0.8
[freezedetect @ 0x2] lavfi.freezedetect.freeze_end: 4
[silencedetect @ 0x3] silence_start: 7.5
[Parsed_ebur128_0 @ 0x4] t: 1.0  M: -20.1 S: -21.0     I: -19.0 LUFS
[Parsed_ebur128_0 @ 0x4] Summary:

  Integrated loudness:
    I:         -14.3 LUFS
    Threshold: -24.5 LUFS

  True peak:
    Peak:       -1.4 dBFS
"""


class QcTest(unittest.TestCase):
    def test_parse_events(self):
        ev = qc.parse_events(FFMPEG_LOG)
        self.assertEqual(ev["black"], [(0.0, 0.4)])
        self.assertEqual(ev["freeze"], [(3.2, 4.0)])
        self.assertEqual(ev["silence"], [(7.5, None)])
        self.assertEqual(ev["lufs"], -14.3)
        self.assertEqual(ev["true_peak"], -1.4)

    def test_evaluate_flags_unplanned_events_only(self):
        info = {
            "format": {"duration": "10.0"},
            "streams": [
                {"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "30/1", "avg_frame_rate": "30/1",
                 "codec_name": "h264", "pix_fmt": "yuv420p"},
                {"codec_type": "audio", "sample_rate": "48000", "channels": 2},
            ],
        }
        spec = tl(audio={"out": "audio/mix.wav"}, qc_allow=[{"kind": "freeze", "start": 3.0, "end": 4.0}])
        checks = {c["name"]: c for c in qc.evaluate(info, qc.parse_events(FFMPEG_LOG), spec)}
        self.assertTrue(checks["resolution"]["ok"] and checks["loudness"]["ok"] and checks["true peak"]["ok"])
        self.assertTrue(checks["no unplanned freeze"]["ok"])
        self.assertFalse(checks["no unplanned black"]["ok"])
        self.assertFalse(checks["no unplanned silence"]["ok"])


if __name__ == "__main__":
    unittest.main()
