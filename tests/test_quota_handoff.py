"""Tests for plugins/quota-handoff/scripts/quota_handoff.py. Run with: python3 -m unittest discover -s tests"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "quota-handoff"
SCRIPT = PLUGIN / "scripts" / "quota_handoff.py"


class QuotaHandoffTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.config = Path(self._tmp.name) / "claude"
        self.config.mkdir()
        self.state = self.config / "quota-handoff"
        self.settings = self.config / "settings.json"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE_", "QUOTA_HANDOFF_"))}
        self.env["CLAUDE_CONFIG_DIR"] = str(self.config)

    def tearDown(self):
        self._tmp.cleanup()

    def run_cmd(self, command, stdin="", **env):
        done = subprocess.run(
            [sys.executable, str(SCRIPT), command],
            input=stdin if isinstance(stdin, str) else json.dumps(stdin),
            capture_output=True,
            text=True,
            env={**self.env, **env},
        )
        self.assertEqual(done.stderr, "")
        return done

    def feed(self, five=None, week=None, reset_in=3600):
        limits = {}
        if five is not None:
            limits["five_hour"] = {"used_percentage": five, "resets_at": time.time() + reset_in}
        if week is not None:
            limits["seven_day"] = {"used_percentage": week, "resets_at": time.time() + reset_in}
        return self.run_cmd("statusline", {"session_id": "s1", "rate_limits": limits})

    def check(self, session="s1", event="PostToolUse", **extra):
        env = {k: v for k, v in extra.items() if k.startswith("CLAUDE_")}
        payload = {"session_id": session, "hook_event_name": event}
        payload.update({k: v for k, v in extra.items() if not k.startswith("CLAUDE_")})
        out = self.run_cmd("check", payload, **env).stdout
        return json.loads(out) if out else None

    # ---- status line

    def test_statusline_saves_limits_and_prints_what_is_left(self):
        done = self.feed(five=42, week=63.4)
        self.assertEqual(done.stdout.strip(), "5h 58% left · week 37% left")
        cache = json.loads((self.state / "rate-limits.json").read_text())
        self.assertEqual(cache["five_hour"]["used_percentage"], 42)
        self.assertEqual(cache["seven_day"]["used_percentage"], 63.4)

    def test_statusline_without_limits_keeps_the_saved_ones(self):
        self.feed(five=42, week=63)
        done = self.run_cmd("statusline", {"session_id": "s2"})
        self.assertIn("no quota data yet", done.stdout)
        self.assertEqual(json.loads((self.state / "rate-limits.json").read_text())["five_hour"]["used_percentage"], 42)

    def test_statusline_survives_garbage_input(self):
        self.assertEqual(self.run_cmd("statusline", "not json").returncode, 0)
        self.assertEqual(self.run_cmd("statusline", '{"rate_limits": {"five_hour": {"used_percentage": "x"}}}').returncode, 0)

    # ---- check

    def test_check_is_silent_above_the_threshold_and_without_data(self):
        self.assertIsNone(self.check())
        self.feed(five=90, week=50)  # exactly 10% left is not "below 10%"
        self.assertIsNone(self.check())

    def test_check_fires_once_per_session(self):
        self.feed(five=91, week=50)
        out = self.check()
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("5-hour window 9% left", context)
        self.assertIn("HANDOFF.md", context)
        self.assertIn("push the current branch", context)
        self.assertIn("quota-handoff", out["systemMessage"])
        self.assertIsNone(self.check())
        self.assertIsNone(self.check(event="UserPromptSubmit"))
        self.assertIsNotNone(self.check(session="s2", event="UserPromptSubmit"))

    def test_check_fires_on_the_weekly_window(self):
        self.feed(five=10, week=95)
        context = self.check()["hookSpecificOutput"]["additionalContext"]
        self.assertIn("weekly window 5% left", context)
        self.assertNotIn("5-hour window 90% left below", context)

    def test_check_skips_subagents_without_using_up_the_one_shot(self):
        self.feed(five=99)
        self.assertIsNone(self.check(agent_id="a1"))
        self.assertIsNotNone(self.check())

    def test_check_ignores_a_window_that_has_reset(self):
        self.feed(five=99, reset_in=-60)
        self.assertIsNone(self.check())

    def test_check_ignores_other_events(self):
        self.feed(five=99)
        self.assertIsNone(self.check(event="Stop"))
        self.assertIsNotNone(self.check())

    def test_options_change_thresholds_file_and_push(self):
        self.feed(five=75, week=50)
        self.assertIsNone(self.check(CLAUDE_PLUGIN_OPTION_FIVE_HOUR_REMAINING="20"))
        out = self.check(
            CLAUDE_PLUGIN_OPTION_FIVE_HOUR_REMAINING="30",
            CLAUDE_PLUGIN_OPTION_HANDOFF_FILE="docs/handoff.md",
            CLAUDE_PLUGIN_OPTION_PUSH="false",
        )
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("docs/handoff.md", context)
        self.assertIn("Do not push", context)

    def test_threshold_zero_turns_a_window_off(self):
        self.feed(five=100, week=50)
        self.assertIsNone(self.check(CLAUDE_PLUGIN_OPTION_FIVE_HOUR_REMAINING="0"))

    # ---- install / uninstall / sync

    def test_install_wraps_the_existing_statusline_and_uninstall_restores_it(self):
        before = {"model": "x", "statusLine": {"type": "command", "command": "echo OLD-BAR", "padding": 2}}
        self.settings.write_text(json.dumps(before))
        self.run_cmd("install")
        after = json.loads(self.settings.read_text())
        self.assertEqual(after["model"], "x")
        self.assertEqual(after["statusLine"]["padding"], 2)
        self.assertIn("quota_handoff.py", after["statusLine"]["command"])
        self.assertTrue((self.state / "quota_handoff.py").is_file())
        self.assertEqual(json.loads(Path(str(self.settings) + ".quota-handoff.bak").read_text()), before)

        # The stable copy is what Claude Code runs: it saves the quota and draws the old bar.
        done = subprocess.run(
            after["statusLine"]["command"],
            shell=True,
            input=json.dumps({"rate_limits": {"five_hour": {"used_percentage": 12}}}),
            capture_output=True,
            text=True,
            env=self.env,
        )
        self.assertEqual(done.stdout.strip(), "OLD-BAR")
        self.assertEqual(json.loads((self.state / "rate-limits.json").read_text())["five_hour"]["used_percentage"], 12)

        self.assertIn("Already set up", self.run_cmd("install").stdout)
        self.run_cmd("uninstall")
        self.assertEqual(json.loads(self.settings.read_text()), before)

    def test_install_without_settings_and_uninstall_removes_the_entry(self):
        self.run_cmd("install")
        self.assertIn("quota_handoff.py", json.loads(self.settings.read_text())["statusLine"]["command"])
        self.run_cmd("uninstall")
        self.assertNotIn("statusLine", json.loads(self.settings.read_text()))

    def test_install_leaves_a_broken_settings_file_alone(self):
        self.settings.write_text("{ not json")
        done = self.run_cmd("install")
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.settings.read_text(), "{ not json")

    def test_sync_sets_itself_up_once_and_keeps_the_old_statusline(self):
        before = {"model": "x", "statusLine": {"type": "command", "command": "echo OLD-BAR"}}
        self.settings.write_text(json.dumps(before))
        out = json.loads(self.run_cmd("sync").stdout)
        self.assertIn("set itself up", out["systemMessage"])
        self.assertIn("earlier status line", out["systemMessage"])
        self.assertEqual((self.state / "quota_handoff.py").read_bytes(), SCRIPT.read_bytes())
        after = json.loads(self.settings.read_text())
        self.assertIn("quota_handoff.py", after["statusLine"]["command"])
        self.assertEqual(json.loads(Path(str(self.settings) + ".quota-handoff.bak").read_text()), before)
        self.assertEqual(self.run_cmd("sync").stdout, "")  # silent once wired
        self.run_cmd("uninstall")
        self.assertEqual(json.loads(self.settings.read_text()), before)

    def test_sync_without_settings_creates_the_statusline(self):
        out = json.loads(self.run_cmd("sync").stdout)
        self.assertNotIn("earlier status line", out["systemMessage"])
        self.assertIn("quota_handoff.py", json.loads(self.settings.read_text())["statusLine"]["command"])

    def test_sync_stays_out_after_uninstall_until_install(self):
        self.run_cmd("sync")
        self.run_cmd("uninstall")
        self.assertEqual(self.run_cmd("sync").stdout, "")
        self.assertNotIn("statusLine", json.loads(self.settings.read_text()))
        self.assertIn("setup at session start: off", self.run_cmd("status").stdout)
        self.run_cmd("install")
        self.run_cmd("uninstall")
        self.run_cmd("install")
        self.assertIn("quota_handoff.py", json.loads(self.settings.read_text())["statusLine"]["command"])

    def test_sync_only_reminds_when_auto_setup_is_off(self):
        out = json.loads(self.run_cmd("sync", CLAUDE_PLUGIN_OPTION_AUTO_SETUP="false").stdout)
        self.assertIn("/quota-handoff:setup", out["systemMessage"])
        self.assertFalse(self.settings.exists())

    def test_sync_leaves_a_broken_settings_file_alone(self):
        self.settings.write_text("{ not json")
        out = json.loads(self.run_cmd("sync").stdout)
        self.assertIn("couldn't read", out["systemMessage"])
        self.assertEqual(self.settings.read_text(), "{ not json")

    def test_sync_prunes_old_markers(self):
        self.feed(five=99)
        self.check(session="old")
        self.check(session="new")
        old = self.state / "fired" / "old"
        os.utime(old, (time.time() - 8 * 86400,) * 2)
        self.run_cmd("sync")
        self.assertFalse(old.exists())
        self.assertTrue((self.state / "fired" / "new").exists())

    def test_status_reports_wiring_and_limits(self):
        self.assertIn("wired: no", self.run_cmd("status").stdout)
        self.run_cmd("install")
        self.feed(five=40, week=20)
        out = self.run_cmd("status").stdout
        self.assertIn("wired: yes", out)
        self.assertIn("5-hour window: 60% left", out)

    # ---- packaging

    def test_manifest_and_marketplace_agree(self):
        manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
        entry = next(p for p in market["plugins"] if p["name"] == "quota-handoff")
        self.assertEqual(entry["source"], "./plugins/quota-handoff")
        self.assertEqual(entry["version"], manifest["version"])
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
        self.assertEqual(set(hooks), {"SessionStart", "PostToolUse", "UserPromptSubmit"})


if __name__ == "__main__":
    unittest.main()
