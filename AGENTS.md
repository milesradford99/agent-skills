# Notes for coding agents

- Validate everything: `python3 scripts/validate_skills.py && python3 -m unittest discover -s tests`. Both must pass before a PR.
- If the Claude CLI is available, also run `claude plugin validate .`.
- Each skill is one self-contained `skills/<name>/SKILL.md`. The frontmatter `name` must equal the folder name; `description` is ≤1024 characters with no angle brackets.
- A new skill must also be added to `.claude-plugin/marketplace.json` (its own plugin entry) and to the table in `README.md`. The validator fails if the marketplace misses it.
- The marketplace name `milesradford-skills` is what users type after `@`. Don't rename it; installs would break. `agent-skills` is reserved by Claude Code, so it can't be used.
- Bump `version` in the plugin entry and add a `CHANGELOG.md` line for any change to a skill's behavior.
- Dated product facts live in each skill's "Facts as of" section. When you re-verify one, update its date.
- Never commit secrets, `.env*` files or `*.local.*` files.
