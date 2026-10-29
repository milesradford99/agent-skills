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
import frames  # noqa: E402
import music  # noqa: E402
import qc  # noqa: E402
import sfx  # noqa: E402
import timeline  # noqa: E402

STARTER = json.loads((KIT / "starter" / "timeline.json").read_text(encoding="utf-8"))


def tl(**overrides):
    base = {
        "meta": {"width": 1920, "height": 1080, "fps": 30, "duration": 10.0, "seed": "s"},
        "audio": {"bpm": 120, "offset": 0.0, "music": "audio/music.wav"},
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

    def test_missing_music_warns_unless_user_declined(self):
        _, warnings = timeline.check(tl(audio={"bpm": 120}))
        self.assertTrue(any("no music bed" in w for w in warnings))
        _, warnings = timeline.check(tl(audio={"bpm": 120, "no_music": "user wants silence"}))
        self.assertFalse(any("no music bed" in w for w in warnings))

    def test_caption_reading_speed(self):
        fast = [{"start": 1.0, "end": 2.0, "text": "下次医生劝你少做一项检查，他的建议跟收入无关。"}]
        _, warnings = timeline.check(tl(captions=fast))
        self.assertTrue(any("needs ~" in w for w in warnings))
        ok = [{"start": 1.0, "end": 4.0, "text": "Start with a line."}]
        _, warnings = timeline.check(tl(captions=ok))
        self.assertFalse(any("needs ~" in w for w in warnings))


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


    def test_cue_layers_each_land_their_transient_on_the_cue(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            audio.write_wav(project / "audio" / "sfx" / "riser.wav", audio.sfx("riser", dur=1.0))
            audio.write_wav(project / "audio" / "sfx" / "sub.wav", audio.sfx("subdrop", dur=0.5))
            spec = tl(audio={"out": "audio/mix.wav"}, cues=[{"id": "hit", "t": 4.0, "gain_db": -6, "sfx": [
                "audio/sfx/riser.wav", {"path": "audio/sfx/sub.wav", "gain_db": -3, "len": 0.4}]}])
            graph = audio.build_mix(spec, project)
            graph = graph[graph.index("-filter_complex") + 1]
            lead = audio.file_transient(project / "audio" / "sfx" / "riser.wav")
            self.assertIn(f"volume=-6dB,adelay={round((4.0 - lead) * 1000)}:all=1", graph)
            self.assertIn("atrim=0:0.4,afade=t=out:st=0.320:d=0.080,volume=-9dB", graph)
            self.assertIn("amix=inputs=2", graph)

    def test_sfx_layer_shape_and_license_log_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "licenses.json").write_text(json.dumps([{"path": "audio/sfx/fs1-pop.wav"}]))
            cues = [{"id": "a", "t": 1.0, "sfx": [{"gain_db": -3}]},
                    {"id": "b", "t": 2.0, "sfx": {"path": "audio/sfx/x.wav", "len": 0}},
                    {"id": "c", "t": 3.0, "sfx": "audio/sfx/fs1-pop.wav"},
                    {"id": "d", "t": 4.0, "sfx": "audio/sfx/fs2-thud.wav"}]
            errors, warnings = timeline.check(tl(cues=cues), project)
            self.assertTrue(any("'a' has an sfx layer with no path" in e for e in errors))
            self.assertTrue(any("'b'" in e and "len > 0" in e for e in errors))
            self.assertEqual([w for w in warnings if "licenses.json" in w],
                             ["cue 'd' uses audio/sfx/fs2-thud.wav, which licenses.json doesn't list (sfx.py get logs it)"])


class SfxTest(unittest.TestCase):
    PAYLOAD = {"results": [
        {"id": 1, "name": "Thud", "duration": 3.2, "num_downloads": 900, "avg_rating": 4.9, "num_ratings": 6,
         "license": "http://creativecommons.org/publicdomain/zero/1.0/", "username": "a",
         "description": "<p>Big   cinematic</p> rumble", "previews": {"preview-hq-mp3": "https://x/1-hq.mp3"}},
        {"id": 2, "name": "Cork pop", "duration": 0.4, "num_downloads": 5000, "avg_rating": 4.4, "num_ratings": 380,
         "license": "https://creativecommons.org/licenses/by/4.0/", "username": "b",
         "description": "cork from a wine bottle, Zoom H5", "previews": {"preview-hq-mp3": "https://x/2-hq.mp3"}},
        {"id": 3, "name": "Pop", "duration": 0.2, "num_downloads": 900, "avg_rating": 4.0, "num_ratings": 40,
         "license": "http://creativecommons.org/licenses/by-nc/3.0/", "username": "c", "description": "",
         "previews": {}},
    ]}

    def test_licenses_are_named_and_screened_for_commercial_use(self):
        names = [r["license"] for r in sfx.parse_results(self.PAYLOAD)]
        self.assertEqual(names, ["CC0", "CC-BY-4.0", "CC-BY-NC-3.0"])
        self.assertEqual([sfx.commercial_ok(n) for n in names + ["Sampling+"]], [True, True, False, False])

    def test_rank_prefers_downloads_then_votes_and_drops_duplicates(self):
        rows = sfx.parse_results(self.PAYLOAD)
        ranked = sfx.rank(rows + rows[:1])
        self.assertEqual([r["id"] for r in ranked], [2, 3, 1])  # same downloads: 40 votes beat 6
        self.assertEqual(rows[0]["desc"], "Big cinematic rumble")
        line = sfx.format_row(ranked[0])
        self.assertIn("↓5000 ★4.4(380)", line)
        self.assertNotIn("https://", line)

    def test_filter_combines_license_and_duration(self):
        self.assertEqual(sfx.filter_string("cc0", None, 2), 'license:"Creative Commons 0" duration:[0 TO 2]')
        self.assertEqual(sfx.filter_string("any", 0.1, None), "duration:[0.1 TO *]")
        self.assertEqual(sfx.filter_string("any", None, None), "")

    def test_license_log_credits_by_and_replaces_by_path(self):
        rows = {r["id"]: r for r in sfx.parse_results(self.PAYLOAD)}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "licenses.json"
            path.write_text(json.dumps([{"path": "audio/music.wav", "license": "original"}]))
            sfx.log_licenses(path, [sfx.license_entry(rows[1], "audio/sfx/a.wav")])
            sfx.log_licenses(path, [sfx.license_entry(rows[2], "audio/sfx/a.wav")])
            log = json.loads(path.read_text())
        self.assertEqual([e["path"] for e in log], ["audio/music.wav", "audio/sfx/a.wav"])
        self.assertEqual(log[1]["attribution"], '"Cork pop" by b (https://freesound.org/s/2/), CC-BY-4.0')
        self.assertIsNone(sfx.license_entry(rows[1], "x")["attribution"])

    def test_measure_reports_transient_ring_and_band(self):
        click = sfx.measure(audio.sfx("click"), 48000)
        sub = sfx.measure(audio.sfx("subdrop", dur=1.5), 48000)
        self.assertLess(click["transient"], 0.01)
        self.assertLess(click["ring"], 0.1)
        self.assertGreater(click["high"] + click["mid"], click["low"])
        self.assertGreater(sub["low"], 0.8)
        self.assertGreater(sub["ring"], click["ring"])
        self.assertIn("(low)", sfx.describe(sub))


class MusicTest(unittest.TestCase):
    def test_derived_arc_rests_before_the_signature(self):
        spec = tl(cues=[{"id": "hook", "t": 0.5, "kind": "hook"}, {"id": "sig", "t": 6.5, "kind": "signature"}])
        sections = music.derive_sections(spec)
        self.assertEqual(music.energy_at(sections, 0.1), 0)
        self.assertEqual(music.energy_at(sections, 6.5 - 0.5), 0)  # the held beat before the payoff
        self.assertEqual(music.energy_at(sections, 7.0), 3)
        self.assertEqual(music.energy_at(sections, 9.9), 1)

    def test_compose_fits_duration_with_headroom(self):
        if music.np is None:
            self.skipTest("numpy not installed")
        spec = tl(cues=[{"id": "hook", "t": 0.5, "kind": "hook"}, {"id": "sig", "t": 6.5, "kind": "signature"}])
        spec["meta"]["duration"] = 4.0
        x = music.compose(spec, "warm")
        self.assertEqual(x.shape, (2, 4 * music.RATE))
        self.assertAlmostEqual(float(abs(x).max()), 10 ** (-6 / 20), places=3)

    def test_every_groove_preset_resolves(self):
        for name in music.GROOVES:
            spec = tl(audio={"bpm": 120, "grooves": [{"start": 0, "end": 4, "groove": name}]})
            self.assertTrue(music.groove_events(spec), name)

    def test_groove_events_sit_on_the_pattern_grid(self):
        spec = tl(audio={"grooves": [{"start": 2, "end": 4, "groove": "rock", "bpm": 120}]})
        kicks = [e["t"] for e in music.groove_events(spec) if e["lane"] == "kick"]
        # rock kick "X...x.x." in eighths at 120 bpm: 0, 1.0, 1.5 s into each 2 s bar
        self.assertEqual(kicks, [2.0, 3.0, 3.5])
        self.assertTrue(all(2 <= e["t"] < 4 for e in music.groove_events(spec)))

    def test_custom_lanes_set_the_bar_length_and_swing(self):
        spec = tl(audio={"grooves": [{"start": 0, "end": 3.5, "bpm": 120, "per_beat": 2,
                                      "lanes": {"kick": "X.x.x..", "hat": "xx|xxxxx"}, "swing": 0.5}]})
        events = music.groove_events(spec)
        bars = {e["bar"] for e in events}
        self.assertEqual(bars, {0, 1})  # 7 eighths at 120 bpm = 1.75 s per bar
        hats = [e["t"] for e in events if e["lane"] == "hat" and e["bar"] == 0]
        self.assertAlmostEqual(hats[1], 0.25 + 0.125)  # off-step pushed half a step late
        self.assertTrue(events[0]["accent"])

    def test_bad_grooves_are_reported_by_timeline_check(self):
        cases = [
            [{"start": 0, "end": 4, "groove": "polka"}],
            [{"start": 0, "end": 4, "lanes": {"kick": "x...", "hat": "xxx"}}],
            [{"start": 0, "end": 4, "lanes": {"cowbell": "x..."}}],
            [{"start": 0, "end": 5, "groove": "rock"}, {"start": 4, "end": 8, "groove": "funk"}],
            [{"start": 8, "end": 12, "groove": "rock"}],
        ]
        for grooves in cases:
            errors, _ = timeline.check(tl(audio={"bpm": 120, "music": "m.wav", "grooves": grooves}))
            self.assertEqual(len(errors), 1, grooves)
        errors, _ = timeline.check(tl(audio={"bpm": 120, "music": "m.wav", "grooves": [{"start": 0, "end": 4, "groove": "waltz"}]}))
        self.assertEqual(errors, [])

    def test_chapters_must_be_sorted_and_inside_the_runtime(self):
        ok = [{"id": "01", "start": 0}, {"id": "02", "start": 4}]
        self.assertEqual(timeline.check(tl(chapters=ok))[0], [])
        self.assertEqual(len(timeline.check(tl(chapters=ok[::-1]))[0]), 1)
        self.assertEqual(len(timeline.check(tl(chapters=[{"id": "01", "start": 12}]))[0]), 1)

    def test_compose_with_grooves_mutes_the_bed_inside_windows(self):
        if music.np is None:
            self.skipTest("numpy not installed")
        spec = tl(cues=[], audio={"bpm": 120, "grooves": [{"start": 1, "end": 3, "groove": "heartbeat"}]})
        spec["meta"]["duration"] = 4.0
        x = music.compose(spec, "warm")
        self.assertEqual(x.shape, (2, 4 * music.RATE))
        mask = music.bed_mask(spec, 4 * music.RATE)
        self.assertEqual(mask[2 * music.RATE], 0.0)
        self.assertEqual(mask[int(3.5 * music.RATE)], 1.0)


class FramesTest(unittest.TestCase):
    def test_sheet_density_scales_with_length(self):
        self.assertEqual(frames.sheet_fps(10), 2.0)
        self.assertEqual(frames.sheet_fps(222.3), 0.5)
        self.assertEqual(frames.sheet_fps(3600), 0.25)

    def test_bursts_are_capped_and_key_cues_come_first(self):
        cues = [{"id": f"c{i}", "t": i * 1.0, "kind": "hit"} for i in range(178)]
        cues += [{"id": "hook", "t": 0.4, "kind": "hook"}, {"id": "sig", "t": 114.7, "kind": "signature"}]
        moments = frames.pick_moments({"cues": cues, "shots": []}, 10)
        self.assertEqual(len(moments), 10)
        names = [n for _, n in moments]
        self.assertIn("hook", names)
        self.assertIn("sig", names)
        self.assertEqual(moments, sorted(moments))


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
        self.assertEqual(checks["no unplanned freeze"]["level"], "warn")
        self.assertEqual(checks["music bed"]["level"], "warn")
        self.assertFalse(checks["no unplanned black"]["ok"])
        self.assertFalse(checks["no unplanned silence"]["ok"])


if __name__ == "__main__":
    unittest.main()
