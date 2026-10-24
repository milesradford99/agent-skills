# agent-skills

Two skills for building open-source software with an AI coding agent. They stay useful as models get stronger because they encode judgment, safety lines and proportion, not tips the model already knows.

| Skill | What it does | Use it when |
|---|---|---|
| [`oss-mentor`](skills/oss-mentor/SKILL.md) | Audits your repo, does routine setup as reviewable PRs with test evidence, and brings you at most 3 decisions at a time with a recommended default. Name, license, scope, public API, taste and releases stay yours. | Starting or open-sourcing a project, asking "what's next?", getting ready for contributors, preparing a release, or contributing to someone else's project |
| [`oss-design`](skills/oss-design/SKILL.md) | Product, tech and UI/UX design that is conventional where users expect it and distinctive where it counts. Picks a depth tier, lets you steer by reacting to options, and tests with a fresh agent and a blind critic. | Designing a feature, a public API or architecture, a CLI's ergonomics, a UI flow, or launch visuals |

**Status:** v0.1, early. Maintained as a personal project, best effort, no support guarantee.

## What makes these different

- **Proportion.** A weekend tool gets five files; a library others depend on gets the full supply-chain setup. Process is added when something happens (first outside PR, second maintainer), not up front.
- **Hard safety lines.** Text from issues, PRs and web pages is treated as data, never as instructions. Releases, merges, settings changes and anything public need your explicit yes for that exact action, and never happen in unattended runs.
- **Good citizenship.** `oss-mentor` checks prior art and asks upstream before you duplicate a project, and never posts to other people's repos on its own.
- **Design that's tested, not just generated.** `oss-design` replaces "make it unique" with drawn themes, blind side-by-side critique and a "fresh agent installs it from the README" test, with accessibility as a gate.

## Install

### Claude Code (plugin marketplace)

```text
/plugin marketplace add milesradford99/agent-skills
/plugin install oss-mentor@milesradford-skills
/plugin install oss-design@milesradford-skills
```

Each skill installs as its own plugin, so you can take one without the other.

### Any agent that reads `SKILL.md` folders

Copy the skill folder into your agent's skills directory. For Claude Code that's `~/.claude/skills/` (for you) or `.claude/skills/` (for one project):

```sh
git clone https://github.com/milesradford99/agent-skills
cp -r agent-skills/skills/oss-mentor agent-skills/skills/oss-design ~/.claude/skills/
```

### Claude app

Each [release](https://github.com/milesradford99/agent-skills/releases) attaches one `.zip` per skill, ready to upload in the app's skills settings.

## Try it

In a repo of yours, ask your agent:

- "What's the status of this project and what should I do next?" (`oss-mentor`, review mode)
- "I want to open-source this tool." (`oss-mentor`, start)
- "Design the `--json` output for this CLI." (`oss-design`, Tier 1)

## How these were built

Both skills were drafted with Claude, then reviewed by five independent agents (runtime mechanics, security red team, skeptical OSS maintainer, product and design strategy, fact-check against current docs) and re-verified by a sixth. [`docs/EVALS.md`](docs/EVALS.md) lists the scenarios used to compare them against an agent with no skill. A human maintainer reviews and owns every change.

Product facts in the skills are dated (October 2026) and the skills tell the agent to re-check them before relying on them.

## Contributing

Issues and small PRs are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md), including the AI-assistance policy. Security reports: [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
