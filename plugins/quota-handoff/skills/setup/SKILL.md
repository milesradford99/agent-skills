---
name: setup
description: Sets up, checks or removes the quota-handoff status line hookup. Use when the user runs /quota-handoff:setup, asks to activate, check or uninstall quota-handoff, or asks why the quota handoff didn't fire.
disable-model-invocation: true
---

# quota-handoff setup

quota-handoff needs the status line, because that is the only place Claude Code hands out the subscription quota. This skill points the user's status line at the plugin's script. An existing status line keeps drawing the bar; the script runs it after saving the quota.

Pick the action from what the user asked. With no argument, install.

| The user wants | Run |
|---|---|
| Set up, activate, install (default) | `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/quota_handoff.py" install` |
| Check that it works, see the quota or thresholds | `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/quota_handoff.py" status` |
| Remove, undo, uninstall | `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/quota_handoff.py" uninstall` |

Run the one command and show the user its output as is. `install` and `uninstall` edit `statusLine` in the user's `~/.claude/settings.json` and leave a backup beside it; they change nothing else.

Then tell the user what applies:

- After `install`: quota data arrives after Claude's next reply. The thresholds, the handoff file name and whether to push are plugin options, changed in `/config`.
- If `status` shows no quota data: it only exists for Pro, Max and Ultra subscriptions in an interactive session, after the first reply. It is absent with an API key and under `claude -p`. A `statusLine` in the project's `.claude/settings.json` overrides the user's one, so the plugin never sees the quota in that project until that entry is removed or pointed at the same command.
- After `uninstall`: the plugin's hooks stay until the user runs `/plugin uninstall quota-handoff@milesradford-skills`, but they do nothing without quota data.

If `python3` isn't found, say so and stop; the plugin needs Python 3.9 or later on the PATH.
