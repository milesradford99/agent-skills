#!/usr/bin/env python3
"""quota-handoff: tell Claude Code to stop and hand off before the subscription quota runs out.

Standard library only. One file, six subcommands:

    statusline   Status line command. Saves the rate limits Claude Code passes on stdin,
                 then prints a short line (or runs the status line you had before).
    check        Hook command (PostToolUse, UserPromptSubmit). Fires once per session
                 when the 5-hour or weekly quota left is below its threshold.
    sync         Hook command (SessionStart). Keeps the stable copy of this script
                 current and wires the status line the first time, unless the
                 auto_setup option is off or the user ran uninstall.
    install      Point the user's status line at this script, keeping the old one.
    uninstall    Put the old status line back.
    status       Show the wiring, the thresholds and the last saved rate limits.

Only the status line receives rate limits, and only hooks can talk to Claude, so the
status line writes them to a file and the hook reads it.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_NAME = "quota_handoff.py"
WINDOWS = (
    # key in rate_limits, label, plugin option holding the threshold
    ("five_hour", "5-hour", "FIVE_HOUR_REMAINING"),
    ("seven_day", "weekly", "WEEK_REMAINING"),
)
DEFAULT_THRESHOLD = 10.0
DEFAULT_HANDOFF_FILE = "HANDOFF.md"
MARKER_MAX_AGE = 7 * 24 * 3600
WRAPPED_TIMEOUT = 10


# ---------------------------------------------------------------- paths


def config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def state_dir() -> Path:
    return Path(os.environ.get("QUOTA_HANDOFF_DIR") or config_dir() / "quota-handoff")


def settings_path() -> Path:
    return config_dir() / "settings.json"


def cache_path() -> Path:
    return state_dir() / "rate-limits.json"


def saved_path() -> Path:
    return state_dir() / "config.json"


def stable_script() -> Path:
    return state_dir() / SCRIPT_NAME


# ---------------------------------------------------------------- small helpers


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def is_ours(statusline) -> bool:
    return isinstance(statusline, dict) and SCRIPT_NAME in str(statusline.get("command", ""))


def our_command() -> str:
    return f'python3 "{stable_script()}" statusline'


def sync_script() -> None:
    """Copy this file to a path that survives plugin updates."""
    source = Path(__file__).resolve()
    target = stable_script()
    if source == target.resolve():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        if target.read_bytes() == source.read_bytes():
            return
    except OSError:
        pass
    tmp = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    shutil.copyfile(source, tmp)
    os.replace(tmp, target)


# ---------------------------------------------------------------- rate limits


def extract_windows(rate_limits) -> dict:
    """Keep only well-formed 5-hour and weekly windows."""
    found = {}
    if not isinstance(rate_limits, dict):
        return found
    for key, _label, _option in WINDOWS:
        window = rate_limits.get(key)
        if not isinstance(window, dict):
            continue
        used = number(window.get("used_percentage"))
        if used is None:
            continue
        entry = {"used_percentage": used}
        resets_at = number(window.get("resets_at"))
        if resets_at is not None:
            entry["resets_at"] = resets_at
        found[key] = entry
    return found


def live_windows(cache: dict, now: float) -> dict:
    """Windows from the cache that haven't reset yet."""
    live = {}
    for key, window in extract_windows(cache).items():
        resets_at = window.get("resets_at")
        if resets_at is not None and resets_at <= now:
            continue
        live[key] = window
    return live


def save_windows(windows: dict, now: float) -> None:
    if not windows:
        return
    cache = read_json(cache_path())
    merged = live_windows(cache, now)
    merged.update(windows)
    merged["updated_at"] = now
    write_json(cache_path(), merged)


def remaining(window: dict) -> float:
    return max(0.0, min(100.0, 100.0 - window["used_percentage"]))


def threshold(option: str) -> float:
    raw = os.environ.get(f"CLAUDE_PLUGIN_OPTION_{option}", "")
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_THRESHOLD
    return max(0.0, min(100.0, value))


def describe(windows: dict) -> list[str]:
    lines = []
    for key, label, _option in WINDOWS:
        window = windows.get(key)
        if not window:
            continue
        line = f"{label} window: {remaining(window):.0f}% left"
        if "resets_at" in window:
            line += time.strftime(", resets %Y-%m-%d %H:%M", time.localtime(window["resets_at"]))
        lines.append(line)
    return lines


# ---------------------------------------------------------------- statusline


def cmd_statusline() -> int:
    raw = sys.stdin.read()
    now = time.time()
    try:
        data = json.loads(raw)
    except ValueError:
        data = {}
    windows = extract_windows(data.get("rate_limits") if isinstance(data, dict) else None)
    try:
        save_windows(windows, now)
    except OSError:
        pass  # never break the status line over a cache write

    previous = read_json(saved_path()).get("previous_statusline")
    if isinstance(previous, dict) and previous.get("command") and not is_ours(previous):
        try:
            done = subprocess.run(
                previous["command"], shell=True, input=raw, capture_output=True, text=True, timeout=WRAPPED_TIMEOUT
            )
            sys.stdout.write(done.stdout)
            return 0
        except (OSError, subprocess.SubprocessError):
            pass  # fall through to our own line

    parts = []
    for key, label in (("five_hour", "5h"), ("seven_day", "week")):
        if key in windows:
            parts.append(f"{label} {remaining(windows[key]):.0f}% left")
    print(" · ".join(parts) if parts else "quota-handoff: no quota data yet")
    return 0


# ---------------------------------------------------------------- check (hook)


def handoff_message(low: list[str], windows: dict) -> str:
    handoff_file = os.environ.get("CLAUDE_PLUGIN_OPTION_HANDOFF_FILE", "").strip() or DEFAULT_HANDOFF_FILE
    push = os.environ.get("CLAUDE_PLUGIN_OPTION_PUSH", "true").strip().lower() not in ("false", "0", "no")
    status = "\n".join(f"- {line}" for line in describe(windows))
    if push:
        git_step = (
            "3. If this is a git repository with changes: commit the work in progress together with the "
            "handoff document (say in the message that it is a work-in-progress handoff) and push the current "
            "branch to its remote. If you are on the default branch and the user has not been committing there "
            "in this session, create a branch such as `wip/handoff-YYYYMMDD` first. Never force-push, never "
            "commit secrets. If there is no remote or the push fails, keep the local commit and say so."
        )
    else:
        git_step = (
            "3. If this is a git repository with changes: commit the work in progress together with the "
            "handoff document (say in the message that it is a work-in-progress handoff). Do not push. "
            "Never commit secrets."
        )
    return f"""[quota-handoff] The user's Claude subscription quota is almost used up ({" and ".join(low)} below the threshold they set), so this session may be cut off soon.
{status}

The user installed the quota-handoff plugin so that you stop and hand off before that happens. This notice fires once per session. Do the following now, spending as few tokens as you can:

1. Stop taking on new work. Finish only the edit you are in the middle of so the files are consistent. Do not start long builds, full test suites or subagents.
2. Write or update the handoff document at `{handoff_file}` in the project root, for a new session that remembers nothing of this conversation: the goal; what is done; what is in progress and its exact state; the next steps in order; how to verify; open questions and decisions waiting on the user; the branch, the relevant files and the commands to resume.
{git_step}
4. End your turn with a short message, in the language the user has been using: the quota status above, where the handoff document is, what was committed and pushed (branch and commit), and the first thing the next session should do. Do not go back to the original task unless the user tells you to.

If you have changed nothing in this session and there is nothing to hand off, skip steps 2 and 3 and only tell the user about the quota."""


def claim(session_id: str) -> bool:
    """True the first time a session asks; later calls and other processes get False."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)[:120] or "unknown"
    fired = state_dir() / "fired"
    fired.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(fired / safe, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    os.close(fd)
    return True


def cmd_check() -> int:
    try:
        event = json.loads(sys.stdin.read())
    except ValueError:
        return 0
    if not isinstance(event, dict):
        return 0
    if event.get("agent_id"):
        return 0  # a subagent can't hand off; the main thread gets it at its next tool result
    hook_event = event.get("hook_event_name")
    if hook_event not in ("PostToolUse", "UserPromptSubmit"):
        return 0

    windows = live_windows(read_json(cache_path()), time.time())
    low = []
    for key, label, option in WINDOWS:
        if key in windows and remaining(windows[key]) < threshold(option):
            low.append(f"{label} window {remaining(windows[key]):.0f}% left")
    if not low:
        return 0
    if not claim(str(event.get("session_id", ""))):
        return 0

    out = {
        "systemMessage": f"quota-handoff: {', '.join(low)}. Claude was told to stop and hand off.",
        "hookSpecificOutput": {"hookEventName": hook_event, "additionalContext": handoff_message(low, windows)},
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------- sync (hook)


def prune_markers(now: float) -> None:
    fired = state_dir() / "fired"
    if not fired.is_dir():
        return
    for marker in fired.iterdir():
        try:
            if now - marker.stat().st_mtime > MARKER_MAX_AGE:
                marker.unlink()
        except OSError:
            pass


def option_on(name: str, default: bool = True) -> bool:
    raw = os.environ.get(f"CLAUDE_PLUGIN_OPTION_{name}", "").strip().lower()
    if not raw:
        return default
    return raw not in ("false", "0", "no", "off")


def cmd_sync() -> int:
    try:
        sync_script()
        prune_markers(time.time())
    except OSError:
        return 0
    if is_ours(read_json(settings_path()).get("statusLine")):
        return 0
    if read_json(saved_path()).get("auto_setup_disabled"):
        return 0  # the user ran uninstall; don't wire it back or nag
    manual = "run /quota-handoff:setup so it can read your quota."
    if not option_on("AUTO_SETUP"):
        note = f"quota-handoff is installed but not active: {manual}"
    else:
        settings = load_settings(quiet=True)
        if settings is None:
            note = f"quota-handoff couldn't read {settings_path()}, so it is not active. Fix the file, then {manual}"
        else:
            previous = wire_statusline(settings)
            kept = " Your earlier status line still draws the bar." if previous else ""
            note = (
                f"quota-handoff set itself up: the status line in {settings_path()} now also saves your quota."
                f"{kept} Backup: {settings_path().name}.quota-handoff.bak. Undo: /quota-handoff:setup uninstall."
            )
    print(json.dumps({"systemMessage": note}))
    return 0


# ---------------------------------------------------------------- install / uninstall / status


def load_settings(quiet: bool = False) -> dict | None:
    path = settings_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        if not quiet:
            print(f"Can't read {path}: {err}. Fix the file and run this again; nothing was changed.")
        return None
    if not isinstance(data, dict):
        if not quiet:
            print(f"{path} isn't a JSON object; nothing was changed.")
        return None
    return data


def backup_settings() -> None:
    path = settings_path()
    if path.exists():
        shutil.copyfile(path, path.with_name(path.name + ".quota-handoff.bak"))


def wire_statusline(settings: dict) -> str | None:
    """Point statusLine at this script. Returns the earlier status line command, if any."""
    current = settings.get("statusLine")
    saved = read_json(saved_path())
    if not is_ours(current):
        # Remember what was there, including "nothing", so uninstall can put it back.
        saved["previous_statusline"] = current if isinstance(current, dict) else None
    saved.pop("auto_setup_disabled", None)
    write_json(saved_path(), saved)

    new = dict(current) if isinstance(current, dict) else {}
    new["type"] = "command"
    new["command"] = our_command()
    backup_settings()
    settings["statusLine"] = new
    write_json(settings_path(), settings)

    previous = saved.get("previous_statusline")
    if isinstance(previous, dict) and previous.get("command"):
        return str(previous["command"])
    return None


def cmd_install() -> int:
    settings = load_settings()
    if settings is None:
        return 1
    sync_script()
    current = settings.get("statusLine")
    if is_ours(current) and current.get("command") == our_command():
        print("Already set up: the status line runs quota-handoff.")
        return 0

    previous = wire_statusline(settings)
    print(f"Status line now runs: {our_command()}")
    if previous:
        print(f"Your earlier status line still draws the bar: {previous}")
    else:
        print("You had no status line, so a short quota line is shown.")
    print(f"Backup of your settings: {settings_path()}.quota-handoff.bak")
    print("Quota data arrives after Claude's next reply in an interactive session.")
    return 0


def cmd_uninstall() -> int:
    settings = load_settings()
    if settings is None:
        return 1
    saved = read_json(saved_path())
    saved["auto_setup_disabled"] = True  # so the next session doesn't wire it back
    write_json(saved_path(), saved)
    if not is_ours(settings.get("statusLine")):
        print("The status line doesn't run quota-handoff; nothing to undo. It won't set itself up again.")
        return 0
    previous = saved.get("previous_statusline")
    backup_settings()
    if isinstance(previous, dict) and previous.get("command"):
        settings["statusLine"] = previous
        print(f"Status line restored to: {previous['command']}")
    else:
        settings.pop("statusLine", None)
        print("Status line removed (you had none before).")
    write_json(settings_path(), settings)
    print("quota-handoff won't set itself up again; run /quota-handoff:setup to turn it back on.")
    print(f"Saved data is still in {state_dir()}; delete that folder to remove it.")
    return 0


def cmd_status() -> int:
    wired = is_ours(read_json(settings_path()).get("statusLine"))
    print(f"Status line wired: {'yes' if wired else 'no (run /quota-handoff:setup)'}")
    if not wired:
        off = read_json(saved_path()).get("auto_setup_disabled") or not option_on("AUTO_SETUP")
        print(f"Automatic setup at session start: {'off' if off else 'on'}")
    for _key, label, option in WINDOWS:
        print(f"Threshold, {label}: fire below {threshold(option):.0f}% left")
    cache = read_json(cache_path())
    lines = describe(live_windows(cache, time.time()))
    if lines:
        for line in lines:
            print(f"Last seen, {line}")
        age = time.time() - (number(cache.get("updated_at")) or 0)
        print(f"Saved {age / 60:.0f} min ago in {cache_path()}")
    else:
        print("No quota data yet. It appears after Claude's first reply in an interactive session,")
        print("and only for Pro, Max and Ultra subscriptions (not API keys, not `claude -p`).")
    return 0


COMMANDS = {
    "statusline": cmd_statusline,
    "check": cmd_check,
    "sync": cmd_sync,
    "install": cmd_install,
    "uninstall": cmd_uninstall,
    "status": cmd_status,
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in COMMANDS:
        print(f"usage: {SCRIPT_NAME} {{{'|'.join(COMMANDS)}}}", file=sys.stderr)
        return 2
    try:
        return COMMANDS[argv[1]]()
    except Exception as err:  # a hook or status line must never take the session down
        if argv[1] in ("install", "uninstall", "status"):
            raise
        print(f"quota-handoff {argv[1]}: {err}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
