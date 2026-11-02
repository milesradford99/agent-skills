# Notes for coding agents

- Validate everything: `python3 scripts/validate_skills.py && python3 -m unittest discover -s tests`. Both must pass before a PR. The tests include the `video-director` kit's Python tools; a change to `references/kit/` needs its tests updated.
- If the Claude CLI is available, also run `claude plugin validate .`.
- Each skill is a `skills/<name>/SKILL.md` that works on its own, plus an optional `skills/<name>/references/` folder for bulky lookup material and tools the skill loads only when a step needs them. Keep SKILL.md lean, and make it say what to do if a reference is missing. The validator fails if SKILL.md mentions a `references/...` path that doesn't exist. The frontmatter `name` must equal the folder name; `description` is ≤1024 characters with no angle brackets.
- A new skill must also be added to `.claude-plugin/marketplace.json` (its own plugin entry) and to the table in `README.md`. The validator fails if the marketplace misses it.
- The marketplace name `milesradford-skills` is what users type after `@`. Don't rename it; installs would break. `agent-skills` is reserved by Claude Code, so it can't be used.
- Bump `version` in the plugin entry and add a `CHANGELOG.md` line for any change to a skill's behavior.
- Dated product facts live in each skill's "Facts as of" section. When you re-verify one, update its date.
- Never commit secrets, `.env*` files or `*.local.*` files.
