# quota-handoff

A Claude Code plugin that stops Claude before your subscription quota runs out. When the 5-hour or the weekly quota left drops below 10%, Claude is told, once per session, to stop, write a handoff document, commit the work in progress and push it. The next session picks up from the document instead of from a half-finished edit.

## How it works

Claude Code gives the quota (`rate_limits`) only to the status line command, and only hooks can put a message in front of Claude. So the plugin has two halves that meet in a file:

1. **Status line**: `quota_handoff.py statusline` saves the 5-hour and weekly usage to `~/.claude/quota-handoff/rate-limits.json` every time the status line refreshes, which is after each assistant message. If you already had a status line, it still draws the bar.
2. **Hooks**: after every tool call (`PostToolUse`) and on every prompt you send (`UserPromptSubmit`), `quota_handoff.py check` reads that file. If either window is below its threshold, it adds the handoff instruction to Claude's context and writes a marker for the session, so it fires once per conversation.

Claude then finishes the edit it is in the middle of, writes `HANDOFF.md` (goal, done, in progress, next steps, how to verify, open questions), commits it with the work in progress, pushes the current branch, and ends its turn with a short report. If you told Claude not to commit, it keeps to that and writes the document only.

## Requirements

- A recent Claude Code (tested on v2.1.325), in an interactive terminal session.
- A Pro, Max or Ultra subscription login. With an API key there is no quota to read.
- `python3` (3.9 or later) on the PATH. No packages needed.

## Install

1. Add the marketplace and install the plugin. In a shell:

   ```bash
   claude plugin marketplace add milesradford99/agent-skills
   ```

   ```bash
   claude plugin install quota-handoff@milesradford-skills
   ```

   Or inside Claude Code: `/plugin marketplace add milesradford99/agent-skills`, then `/plugin install quota-handoff@milesradford-skills`.

2. Start a new Claude Code session. The plugin sets itself up when the session starts: it points `statusLine` in `~/.claude/settings.json` at its script, keeps the status line you had drawing the bar, leaves a backup at `~/.claude/settings.json.quota-handoff.bak`, and says so in one line. It does this once.

   To do this step yourself instead, turn the `auto_setup` option off and run `/quota-handoff:setup`.

3. Send any message, wait for the reply, then check:

   ```text
   /quota-handoff:setup status
   ```

   You should see `Status line wired: yes` and a `Last seen` line for each window. If you had no status line before, the bar now shows something like `5h 58% left · week 37% left`.

## Options

Change them with `/plugin configure quota-handoff@milesradford-skills` or in `/config`.

| Option | Default | Meaning |
|---|---|---|
| `five_hour_remaining` | `10` | Hand off when the 5-hour quota left is below this percentage. `0` turns the window off. |
| `week_remaining` | `10` | The same for the weekly quota. |
| `handoff_file` | `HANDOFF.md` | Where the handoff document goes, relative to the project root. |
| `push` | `true` | Push after committing. `false` commits locally only. |
| `auto_setup` | `true` | Wire the status line at the first session start. `false` leaves it to `/quota-handoff:setup`. |

The handoff itself uses quota: Claude has to write the document and run git with the whole conversation in context. With a long conversation on a small plan, 10% of the 5-hour window can be tight, so raise `five_hour_remaining` to 15 or 20 if a handoff was ever cut off.

## Limits

- **No status line, no data.** `claude -p`, the Agent SDK and cloud sessions don't run a status line, so nothing fires there. The same goes for a project whose `.claude/settings.json` sets its own `statusLine`, since that overrides yours: point it at the same command (`/quota-handoff:setup status` won't show data until you do).
- **It is an instruction, not a kill switch.** Claude is told to stop and almost always does, but nothing blocks further tool calls.
- **The first reading comes after the first reply.** If the quota is already low when a session starts, the handoff fires on the first tool call or your second message. With nothing changed yet, Claude only tells you about the quota.
- **Once per session means per session id.** A resumed or forked session that gets a new id can fire again.
- **Subagents are skipped.** The instruction goes to the main conversation at its next tool result, not to a subagent that can't hand off.
- **One account per machine.** The quota file is shared by all sessions, which is what you want for one account and wrong if you switch accounts between sessions.

## Uninstall

Run `/quota-handoff:setup uninstall` first, so your earlier status line is put back. After that the plugin doesn't set itself up again unless you run `/quota-handoff:setup`. Then:

```bash
claude plugin uninstall quota-handoff@milesradford-skills
```

Saved data stays in `~/.claude/quota-handoff/`; delete the folder to remove it.

## Try it without waiting for the quota

This fakes a 5-hour window at 6% left in a throwaway folder and starts a session that reads it:

```bash
mkdir -p /tmp/qh && echo "{\"five_hour\":{\"used_percentage\":94,\"resets_at\":$(( $(date +%s) + 3000 ))}}" > /tmp/qh/rate-limits.json
```

```bash
QUOTA_HANDOFF_DIR=/tmp/qh claude
```

Ask for any small change in a scratch repository. Claude should stop after its first tool call and hand off.

## Facts as of 2026-11

Checked against the Claude Code docs and v2.1.325:

- The status line input carries `rate_limits.five_hour` and `rate_limits.seven_day`, each with `used_percentage` and `resets_at`, for Pro, Max and Ultra subscribers after the first API response. Hook input has no quota field.
- The status line command re-runs after each assistant message.
- `PostToolUse` and `UserPromptSubmit` hooks can add to Claude's context with `hookSpecificOutput.additionalContext`.
- A plugin manifest can't declare a status line, which is why a `SessionStart` hook edits `statusLine` in the user's settings.
